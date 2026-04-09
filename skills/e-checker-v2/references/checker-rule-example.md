# Checker Rules

## 规则定义

规则按**模块**分组，每个模块下包含多条检查规则，每条规则为一行纯文本描述。

### 格式说明

- 模块名：不包含路径分隔符（`/`、`.`、`:`）的独立行
- 规则行：包含文件路径或表名引用，描述具体检查条件

### 示例

```
梦幻岛检查
activities/mhd2下的mhd2表Mhd2BasicInfo中的ID列，需要在mhd2Shop表有对应的Mhd2Shop和Mhd2ShopReward页签，页签名字后面括号本期的mhdid
activities/mhd2的Mhd2BasicInfo中的ID列不可为空

背包检查
bagskinGift表bagskinGiftInfo里的content字段中第三个奖励的背包的id，需要在manager表ManagerBagSkin里存在
```

## 你的规则

（在此处按模块添加实际检查规则）
