爬取了**Administrative Science Quarterly (ASQ)** 期刊截止到2025年7月5日所有发表论文的基本信息（1999年至2025年，每卷至多4期），包括DOI号、作者、期卷号等。因网站设置反爬虫机制，故采用 ***selenium*** 逻辑爬虫。速度不快，但是爬取效果尚可
> [!TIP]
> 代码支持断点续爬功能，如果程序中断，重新运行时会从上次停止的地方继续
> + 第一次运行，会生成 *ASQ ToC/checkpoint.json* 文件
> + 如果想从头开始爬取，需要删除 *ASQ ToC/checkpoint.json* 文件
> + 断点信息会自动保存在 *ASQ ToC/checkpoint.json* 文件中

> [!WARNING]
> 若用EXCEL直接打开爬取结果（即 *csv* 文件），内容的标点符号会显示乱码，故经过 *txt* 转为正常的 *xlsx* 格式
