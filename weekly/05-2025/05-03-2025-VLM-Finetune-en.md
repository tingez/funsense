# Visual Language Model (VLM) Fine-tuning Experiment: Data Visualization Comparison Task Based on MiniCPM-V Model

**Date:** May 3, 2025  
**Author:** Tinge  
**Topic:** Visual Language Model Fine-tuning and Evaluation

## Introduction

More and more LLMs now support multimodal functionality, incorporating visual and even auditory elements, further expanding the capabilities of large models.

## Model Selection

Given that I currently only have one RTX 4090 and one RTX 3080, I can only experiment with smaller parameter VLMs. After careful consideration, I found that MiniCPM-V-2.6 is a good choice with parameters under 10B. Recently, a new MiniCPM-o-2.6 was also released, supporting image, video, and audio inputs, enabling edge-based AI capabilities. This workshop is still based on the MiniCPM-V-2.6 8B model. The idea is to build a domain-specific dataset, test the zero-shot in-context learning prediction performance, annotate a small-scale fine-tuning dataset, run a round of LoRA fine-tuning, and then compare the prediction results.

## Dataset Construction

### Test Scenario Selection

Selecting test scenarios and building test datasets is a tedious process. The basic idea comes from the "spot the difference" game, where differences should ideally be at the semantic level rather than just pixel-level differences. After searching around, I decided to build one myself.

### Base Dataset

For the base dataset, I referenced the NV2VIS dataset, [nvBench](https://github.com/TsinghuaDatabaseGroup/nvBench), which provides 100+ CSV datasets, 6000+ data query and visualization command statements, and corresponding data analysis charts (pie charts, bar charts, line charts, etc.).

### Data Grouping and Sample Construction

I selected 2 groups of data: a test group with 400+ data points and a train group with 100+ data points. For each record in these groups, samples were constructed as follows:
- The data analysis chart from nvBench is labeled as image_00
- Based on the query statement and corresponding CSV data, a third-party data analysis agent was used to generate another data analysis chart labeled as image_01
- Prompts were constructed to compare the similarity between image_01 and image_00 and explain the reasons

### Sample Annotation

MiniCPM-0-2.6 was used for zero-shot judgment of image similarity, followed by manual corrections. This semi-manual approach annotated over 500 samples.

| Field | Content |
| --- | --- |
| similarity_score | 0.93 |
| difference_summary | The charts have a high semantic similarity with data point values and axis labels. The only notable difference is the order of data points along the x-axis. |

## Model Evaluation and Fine-tuning

### Zero-shot Evaluation

With the annotated data, we can examine the model's zero-shot accuracy on this specific task. The dataset construction might not be very comprehensive, as the model's accuracy on this task is about 56%, only slightly better than random guessing. The next step is to see if fine-tuning the model can improve performance in this scenario.

### Fine-tuning Environment Preparation

I want to give credit to MiniCPM's GitHub project, which provides detailed fine-tuning steps. The process was hindered by my 4090 and 3080 GPUs, first due to package version and CUDA compatibility issues (requiring CUDA 12.1), and second due to insufficient memory. I struggled for a long time with various approaches like DeepSpeed zero2, zero3, offload_optimizer, and offload_param, but couldn't get them to run smoothly.

### LoRA Fine-tuning Process

For LoRA fine-tuning, two 4090s should be sufficient. I decided to rent a cloud server, configured the correct CUDA version and dependent packages, and the fine-tuning process ran smoothly. The fine-tuning training process was also quick, running overnight for about 40 epochs, though it completely overfitted.

### Fine-tuning Effect Evaluation
| Model Status | Test Dataset Accuracy | Notes |
| --- | --- | --- |
| Original Model | 56% | Zero-shot prediction |
| LoRA Fine-tuned Model | 78% | 100 annotated data points, 20 epochs |
