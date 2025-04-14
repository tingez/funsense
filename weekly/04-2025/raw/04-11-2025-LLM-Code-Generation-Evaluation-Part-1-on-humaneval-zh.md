# LLM 代码生成评估第一部分：HumanEval 基准测试
**日期：** 2025年4月11日  
**作者：** Tinge  
**主题：** 评估 LLM 代码生成能力

## 引言
大型语言模型（LLMs）通过利用海量训练数据，已经彻底改变了代码生成领域，能够根据自然语言描述生成类人代码。这些模型能够理解上下文，遵循复杂指令，并在各种编程语言和范式中生成功能正确的代码。

评估 LLM 生成的代码对于确保其质量、正确性和效率至关重要。HumanEval 和 HumanEval+ 等基准测试提供了标准化的测试套件，用于评估 LLM 的代码生成能力，衡量功能正确性、代码质量以及处理边缘情况的能力等因素。这些评估帮助研究人员和开发者了解不同模型的优势和局限性，指导人工智能辅助编程的进一步改进。

## 关于 HumanEval 和 HumanEval+

**HumanEval** 基于 OpenAI 的论文《评估在代码上训练的大型语言模型》。它由一组精心策划的 Python 编程问题组成，这些问题需要根据自然语言提示生成功能正确的代码。

**HumanEval+** 是 **EvalPlus** 项目的一部分，它通过提供更全面的测试用例套件扩展了 HumanEval 基准，显著提高了评估的稳健性。这一增强解决了原始数据集的局限性，能够检测出过拟合或脆弱的代码，这些代码可能通过最小测试但在更广泛的上下文中失败。

这两个基准共同为模型在代码生成任务中的功能正确性和泛化能力提供了更可靠和细致的衡量标准。

## 选定测试的模型

我们选择了几个著名模型来评估其代码生成能力：

### 1. **DeepSeek 模型**
- 比较各种云服务提供商后，DeepSeek 自己的 API 提供了最佳性价比。它在非高峰时段提供有吸引力的折扣。但是，推理速度是一个缺点，明显较慢。虽然 DeepSeek-Chat 的速度可以接受，但 DeepSeek-Reasoner 的性能特别慢。

#### a. **DeepSeek-Chat (V3)**
- **架构**：混合专家系统（MoE）与多头潜在注意力（MLA）和 DeepSeekMoE。
- **总参数量**：671B；**每个 Token 的活跃参数**：37B。
- **特点**：通过选择性专家激活实现高效推理；支持聊天功能。
- **上下文长度**：最多 64K tokens。

#### b. **DeepSeek-Reasoner (R1)**
- **架构**：MoE 与强化学习增强。
- **总参数量**：671B；**每个 Token 的活跃参数**：37B。
- **特点**：为复杂推理任务优化；开源且经济实惠。
- **上下文长度**：最多 64K tokens。

---

### 2. **Meta 的 Llama 4 模型**
- Llama4 模型一直是众多猜测的对象，但其实际性能只能通过测试确定。
- 对于此次评估，我们使用 Together AI 的 API 接口作为测试服务器。

#### a. **Llama 4-Maverick**
- **架构**：MoE 与 128 个专家。
- **总参数量**：约 400B；**每个 Token 的活跃参数**：17B。
- **特点**：多模态能力；在推理和编码任务中表现出色。
- **上下文长度**：最多 1M tokens。

#### b. **Llama 4-Scout**
- **架构**：MoE 与 16 个专家。
- **总参数量**：约 109B；**每个 Token 的活跃参数**：17B。
- **特点**：高效推理；支持多语言和多模态输入。
- **上下文长度**：最多 10M tokens。

---

### 3. **Qwen**
- Qwen coder 模型展示了小型模型在代码生成中的潜力。
- 我们在 Groq 和 Together AI 服务器上都进行了测试，结果略有差异。

#### **Qwen2.5-coder-32B-Instruct**
- **架构**：为代码生成优化的 Transformer 模型。
- **总参数量**：32B。
- **特点**：在代码生成基准测试中表现最佳；与 GPT-4o 相比具有竞争力。

---

### 4. **DeepCoder**
- DeepCoder-14B-Preview 是一个代码推理 LLM，从 DeepSeek-R1-Distilled-Qwen-14B 使用分布式强化学习（RL）进行微调，以扩展到长上下文长度。
- 目前，没有云服务提供商为此模型提供 API 服务，因此它只能在本地 NVIDIA RTX 4090 GPU 上运行。为了测试这个模型，我们投入了大量时间配置 ollama、llama.cpp 和 vllm。最终，只有 FP8 量化才能让我们在可接受的时间内完成整个测试。然而，测试结果不一致，可能是由于配置问题。当条件允许时，我计划重新审视并重新配置设置。

#### **DeepCoder-14B-Preview-fp8**
- **架构**：为代码相关任务设计的 Transformer 模型。
- **总参数量**：14B
- **特点**：利用 FP8 精度进行高效推理；专为代码生成和推理量身定制。

---

## 测试环境 - EvalPlus 项目

- EvalPlus 是一个先进的评估框架，旨在增强对代码生成任务中大型语言模型（LLMs）的评估。EvalPlus 的主要特点包括：
- EvalPlus 支持多种后端，如 openai、vllm 等。
```bash
export OPENAI_API_KEY="{KEY}" # https://platform.deepseek.com/api_keys

evalplus.evaluate --model "deepseek-chat" --dataset humaneval --base-url https://api.deepseek.com --backend openai --greedy

evalplus.evaluate --model "deepseek-reasoner" --dataset humaneval --base-url https://api.deepseek.com --backend openai --greedy

evalplus.evaluate --model "qwen-2.5-coder-32b" --dataset humaneval --base-url https://api.groq.com/openai/v1 --backend openai --greedy

evalplus.evaluate --model "Qwen/Qwen2.5-Coder-32B-Instruct" --dataset humaneval --base-url https://api.together.xyz/v1 --backend openai --greed
```

## 结果
| 模型 | API 服务器 | HumanEval(pass@1) | HumanEval+(额外测试 pass@1) | 持续时间 |
| --- | --- | --- | --- | --- |
| DeepSeek-Chat | DeepSeek | 0.939 | 0.890 | 1:11:35 |
| DeepSeek-Reasoner | DeepSeek | 0.976 | 0.921 | 5:42:18 |
| llama4-maverick | Together AI | 0.872 | 0.811 | 0:10:37 |
| llama4-scout | Together AI | 0.823 | 0.768 | 0:13:24 |
| llama3-3.3-70B-Instruct-Turbo | Together AI | 0.841 | 0.774 | 0:06:05 |
| Qwen-2.5-Coder-32B-Instruct | Groq | 0.927 | 0.878 | 0:11:54 |
| Qwen-2.5-Coder-32B-Instruct | Together AI | 0.902 | 0.860 | 0:11:38 |
| DeepCoder-14B-Preview-fp8(*) | 4090 vllm | < 0.5 | < 0.5 | 0:47:57 |
