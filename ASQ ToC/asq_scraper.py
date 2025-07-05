import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import csv
from time import sleep
import random
import os
import json
import sys

def setup_driver():
    """使用 undetected_chromedriver 设置浏览器"""
    try:
        # 配置 Chrome 选项
        options = uc.ChromeOptions()
        
        # 基本设置
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')  # 禁用图片加载以提高速度
        
        # 设置用户代理 - 使用与您的Chrome版本匹配的版本号
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
        
        # 设置窗口大小
        options.add_argument('--window-size=1920,1080')
        
        # 创建 undetected_chromedriver 实例
        # 指定您的Chrome版本为137
        driver = uc.Chrome(
            options=options,
            version_main=137,  # 指定您的Chrome版本
            headless=True,     # 隐藏浏览器窗口
            use_subprocess=True,
            driver_executable_path=None  # 让 undetected_chromedriver 自动下载匹配的驱动
        )
        
        # 设置页面加载超时
        driver.set_page_load_timeout(60)  # 增加超时时间到60秒
        driver.implicitly_wait(15)  # 增加隐式等待时间
        
        return driver
        
    except Exception as e:
        print(f"启动Chrome浏览器时出错: {str(e)}")
        print("请确保：")
        print("1. Chrome浏览器已正确安装")
        print("2. 已安装 undetected_chromedriver: pip install undetected-chromedriver")
        raise e

def write_to_csv(articles, file_path, is_new=False):
    mode = 'w' if is_new else 'a'
    with open(file_path, mode, newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['Year', 'Volume', 'Issue', 'Title', 'Authors', 'DOI', 'Link'])
        if is_new:  # 只在新文件时写入表头
            writer.writeheader()
        writer.writerows(articles)

def get_year_from_volume(volume):
    # ASQ 官网最早一期是第44卷，1999年，每卷加一年
    return 1956 + (volume - 1)

def scrape_amr_page(volume, issue, max_retries=5):
    """爬取指定卷期的文章，支持重试机制"""
    
    for attempt in range(max_retries):
        driver = None
        try:
            driver = setup_driver()
            
            url = f"https://journals.sagepub.com/toc/asqa/{volume}/{issue}"
            print(f"\n正在访问页面: {url} (尝试 {attempt + 1}/{max_retries})")
            
            # 访问页面
            driver.get(url)
            
            # 等待页面加载 - 增加超时时间
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "issue-item"))
                )
            except:
                # 如果找不到issue-item，尝试其他选择器
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "article-item"))
                    )
                except:
                    print("页面加载超时，尝试刷新页面...")
                    driver.refresh()
                    sleep(5)
                    # 再次尝试等待
                    try:
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "issue-item"))
                        )
                    except:
                        if attempt < max_retries - 1:
                            print(f"第 {attempt + 1} 次尝试失败，准备重试...")
                            if driver:
                                driver.quit()
                            continue
                        else:
                            print("所有重试都失败了")
                            if driver:
                                driver.quit()
                            return []
            
            # 给页面更多时间完全加载
            sleep(random.uniform(3, 5))
            
            # 解析页面内容
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles = []
            
            # 更新选择器以适应新的页面结构
            article_elements = soup.find_all('div', class_='issue-item')
            if not article_elements:
                # 尝试其他可能的选择器
                article_elements = soup.find_all('div', class_='article-item')
            
            print(f"找到 {len(article_elements)} 个文章元素")
            
            for article in article_elements:
                try:
                    # 查找标题链接
                    title_div = article.find('div', class_='issue-item__title')
                    if not title_div:
                        title_div = article.find('h3')  # 尝试其他标题选择器
                    
                    if not title_div:
                        print("跳过：未找到标题div")
                        continue
                        
                    title_link = title_div.find('a')
                    if not title_link:
                        print("跳过：未找到标题链接")
                        continue
                    
                    # 获取标题文本 - 从h5标签中获取
                    title_heading = title_link.find('h5', class_='issue-item__heading')
                    if title_heading:
                        title = title_heading.get_text(strip=True)
                    else:
                        title = title_link.get_text(strip=True)
                    
                    if not title:
                        print("跳过：标题为空")
                        continue
                    
                    # 获取DOI
                    doi = title_link['href'].replace('/doi/abs/', '').replace('/doi/', '').strip()
                    
                    # 根据卷号计算年份
                    year = get_year_from_volume(volume)
                    
                    # 获取作者信息 - 更新选择器
                    authors_list = article.find('ul', class_='rlist--inline loa comma')
                    if authors_list:
                        authors = []
                        for author_li in authors_list.find_all('li'):
                            author_span = author_li.find('span')
                            if author_span:
                                authors.append(author_span.get_text(strip=True))
                        authors = '; '.join(authors)
                    else:
                        authors = ''
                    
                    # 更新链接格式
                    link = f"https://journals.sagepub.com{title_link['href']}"
                    
                    articles.append({
                        'Year': year,
                        'Volume': volume,
                        'Issue': issue,
                        'Title': title.replace('\n', ' '),
                        'Authors': authors,
                        'DOI': doi,
                        'Link': link
                    })
                    
                    print(f"成功解析文章：{title[:50]}...")
                    
                except Exception as e:
                    print(f"解析文章时出错: {str(e)}")
                    continue
            
            # 如果成功获取到文章，返回结果
            if articles:
                driver.quit()
                return articles
            else:
                print("未找到任何文章，可能是页面结构问题")
                if attempt < max_retries - 1:
                    print(f"第 {attempt + 1} 次尝试失败，准备重试...")
                    driver.quit()
                    continue
                else:
                    print("所有重试都失败了")
                    driver.quit()
                    return []
                    
        except Exception as e:
            print(f"爬取 Volume {volume}, Issue {issue} 时出错: {str(e)}")
            if driver:
                driver.quit()
            if attempt < max_retries - 1:
                print(f"第 {attempt + 1} 次尝试失败，准备重试...")
                continue
            else:
                return []
    
    return []

def load_checkpoint():
    checkpoint_file = 'checkpoint.json'
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return {'last_volume': 44, 'last_issue': 0}  # 默认从第1卷开始

def save_checkpoint(volume, issue):
    checkpoint_file = 'checkpoint.json'
    with open(checkpoint_file, 'w') as f:
        json.dump({'last_volume': volume, 'last_issue': issue}, f)

def main():
    output_file = 'asq_articles.csv'
    total_articles = 0
    
    # 检查是否需要创建新文件
    is_new_file = not os.path.exists(output_file)
    
    # 确保输出目录存在（只有当文件路径包含目录时才创建）
    output_dir = os.path.dirname(output_file)
    if output_dir:  # 只有当目录不为空时才创建
        os.makedirs(output_dir, exist_ok=True)
    
    # 检查是否需要重置断点
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("重置断点，将从第1卷第1期开始爬取...")
        if os.path.exists('checkpoint.json'):
            os.remove('checkpoint.json')
            print("已删除断点文件")
    
    # 加载断点信息
    checkpoint = load_checkpoint()
    start_volume = checkpoint['last_volume']
    start_issue = checkpoint['last_issue'] + 1
    if start_issue > 4:  # 如果上次完成了某卷的最后一期
        start_volume += 1
        start_issue = 1
    
    print(f"将从第 {start_volume} 卷第 {start_issue} 期开始爬取...")
    
    try:
        for volume in range(start_volume, 70):  # 修改为爬取到第49卷 (range的结束值要比目标大1)
            for issue in range(start_issue, 5):
                print(f"\n正在爬取第 {volume} 卷第 {issue} 期...")
                articles = scrape_amr_page(volume, issue)
                
                if articles:
                    write_to_csv(articles, output_file, is_new=(is_new_file and total_articles == 0))
                    total_articles += len(articles)
                    print(f"本期成功爬取 {len(articles)} 篇文章")
                    print(f"当前总计已爬取 {total_articles} 篇文章")
                    
                    latest_article = articles[-1]
                    print("\n最新爬取文章信息：")
                    print(f"年份：{latest_article['Year']}")
                    print(f"标题：{latest_article['Title']}")
                    print(f"作者：{latest_article['Authors']}")
                    print(f"DOI：{latest_article['DOI']}")
                
                # 保存断点
                save_checkpoint(volume, issue)
                
                # 增加更长的随机延迟来避免触发反爬虫机制
                sleep_time = random.uniform(5, 10)
                print(f"等待 {sleep_time:.1f} 秒...")
                sleep(sleep_time)
            
            # 重置下一卷的起始期数为1
            start_issue = 1
        
        print(f"\n爬取完成！共爬取 {total_articles} 篇文章")
        print(f"数据已保存到 {output_file}")
        
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        # 保存当前进度
        save_checkpoint(volume, issue)
        print("已保存断点信息，下次运行从此处继续")

if __name__ == "__main__":
    main() 