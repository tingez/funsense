# 视觉语言模型（VLM）微调实验：基于MiniCPM-V模型的数据可视化对比任务

**日期：** 2025年5月3日  
**作者：** Tinge  
**主题：** 视觉语言模型微调与评估

## 引言

越来越多的LLM支持multimodal的功能了，加入了视觉甚至听觉元素，大模型的能力范围进一步获得扩展。

## 模型选择

鉴于目前手头上只有一块4090和3080，只能尝试一些小规模参数的VLM，选来选去，发现面壁的MiniCPM-V-2.6，在10B以下参数，是不错的选择。最近也发布了新的MiniCPM-o-2.6，支持图片，视频以及语音类型的输入，支持端侧的AI能力。本篇的workshop还是基于MiniCPM-V-2.6 8B模型。想法是构建一个特定领域的数据集，测试一下zero-shot in context learning的预测效果，标注一个小规模finetune数据集，跑一轮lora finetue，再对比一下预测效果。

## 数据集构建

### 测试场景选择

测试场景选取以及测试数据集构建是一个繁琐的过程。基本idea源自"找不同"游戏，最好不仅仅是像素级别的不同，而是视觉上存在一些语义层面的区别，找来找去，不如自己构建一个了。

### 基础数据集

基础数据集的选择：参考了一个NV2VIS的的数据集，[nvBench](https://github.com/TsinghuaDatabaseGroup/nvBench)，这个数据集提供的100+个CVS数据，6000+的数据查询并可视化的命令语句，以及对应生成的数据分析图(饼图，柱状图和曲线图等)。

### 数据分组和样本构建

分别挑选了2组数据，400+条数据的test group和100+数据的train group。对于2个group中的每一条记录，通过如下方式构建样本：
- nvBench中的数据分析图为image_00
- 根据查询语句和对应CVS数据，找一个第三方的数据分析Agent来再生成数据分析图image_01
- 构建prompt来对比image_01和image_00的相似度和原因

### 样本标注

让MiniCPM-0-2.6 zeroshot 判断对比图片的相识度，然后人工进行纠正，这样半手工的方式标注了500+个样本。

| 字段  | 内容 |
| --- | --- |
| similarity_score | 0.93 |
| difference_summary | The charts have a high semantic similarity with data point values and axis labels. The only notable difference is the order of data points along the x-axis. |


## 模型评估与微调

### Zero-shot评估

有了标注数据，就可以看看模型在这个特定任务上zeroshot的准确率情况了。可能数据集本身构建的就不是很完备，在这个任务上，模型的准确率大约在56%，略好于盲猜。下一步就是看一看这样的虚构场景，模型finetue一下，还有没有的救。

### 微调环境准备

这里要给个面壁点个赞，github项目中提供了详细的finetue步骤。整个过程被我的4090和3080拖了后腿，首先是各种包的版本以及cuda的匹配问题，其次是内存不够的问题，折腾了很久，什么deepspeed zero2，zero3，什么offload_optimizer，offload_param，都没有办法顺利跑起来。

### LoRA微调过程

lora微调的话，2块4090应该是够用了，果断出手，租一个云服务器了，配置正确的cuda版本和依赖的包，很顺利微调的流程就跑起来了。微调训练过程也很快，跑了一个晚上，大约40个epoch，就完全的过拟了。

### 微调效果评估
| 模型情况 | 测试数据集准确率 | 说明 |
| --- | --- | --- |
| 原始模型 | 56% | zero shot预测 |
| LoRA微调模型 | 78% | 100条标注数据，20 epoch |