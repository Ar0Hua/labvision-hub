# Step 63：颜色和亮度检索条件

- SearchIntent 增加 targetColor (#RRGGBB)、colorTolerance（各 RGB 通道默认48）及 brightness（dark/normal/bright），支持多轮保留和重置。
- SQL 参数绑定主色 RGB 区间；亮度仅使用 READY 且源版本匹配的 feature。向量召回使用相同颜色范围和亮度阈值，最终鉴权后复核当前字段。
- 阈值：dark <50、normal 50～210、bright >210，基于索引图像而不是原始文件；缺失特征不通过。
- Worker 新增 colorR/G/B payload，schema 增加三个整数索引及 brightnessScore 浮点索引；旧数据需回填，未在本轮执行。
- 当前颜色是可解释的粗粒度通道范围，不是 Lab/CIEDE2000 感知色差。范围 SQL 仍待真实 MySQL 联调。
- Python 88 项及 Java Agent 回归通过；未部署、未执行数据库迁移。
