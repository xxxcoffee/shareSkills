# Checker Rules

## 规则定义

规则按**模块**分组，每个模块下包含多条检查规则，每条规则为一行纯文本描述。

### 格式说明

- 模块名：不包含路径分隔符（`/`、`.`、`:`）的独立行
- 规则行：包含文件路径或表名引用，描述具体检查条件

### 示例

```
活动模块检查
activities/event表EventBasicInfo中的ID列，需要在eventShop表有对应的EventShop和EventShopReward页签
activities/event的EventBasicInfo中的ID列不可为空

道具检查
itemGift表itemGiftInfo里的content字段中第三个奖励的道具id，需要在manager表ManagerItem里存在
```

## 你的规则

（在此处按模块添加实际检查规则）
