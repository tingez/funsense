# LLM Code Generation Evaluation Part 1: HumanEval Benchmark
**Date:** April 11, 2025  
**Author:** Tinge  
**Topic:** Evaluating LLM Code Generation Capabilities

## Introduction
Large Language Models (LLMs) have revolutionized code generation by leveraging vast amounts of training data to produce human-like code from natural language descriptions. These models can understand context, follow complex instructions, and generate functionally correct code across various programming languages and paradigms.

Evaluating LLM-generated code is crucial to ensure its quality, correctness, and efficiency. Benchmarks like HumanEval and HumanEval+ provide standardized test suites to assess an LLM's code generation capabilities, measuring factors such as functional correctness, code quality, and the ability to handle edge cases. These evaluations help researchers and developers understand the strengths and limitations of different models, guiding further improvements in AI-assisted programming.

## About HumanEval and HumanEval+

**HumanEval** is based on OpenAI's paper "Evaluating Large Language Models Trained on Code." It consists of a curated set of Python programming problems that require generating functionally correct code from natural language prompts.

**HumanEval+**, developed as part of the **EvalPlus** project, extends the HumanEval benchmark by providing a more comprehensive suite of test cases, significantly improving the robustness of evaluation. This enhancement addresses limitations in the original dataset by detecting overfitted or brittle code that may pass minimal tests but fail in broader contexts.

Together, these benchmarks offer a more reliable and nuanced measure of a model's functional correctness and generalization in code generation tasks.

## Models Selected for Testing

We've selected several prominent models to evaluate their code generation capabilities:

### 1. **DeepSeek Models**
- After comparing various cloud service providers, DeepSeek's own API offers the best value for money. It provides attractive discounts during off-peak hours. However, the inference speed is a drawback, being notably slow. While DeepSeek-Chat's speed is acceptable, DeepSeek-Reasoner's performance is particularly slow.

#### a. **DeepSeek-Chat (V3)**
- **Architecture**: Mixture-of-Experts (MoE) with Multi-head Latent Attention (MLA) and DeepSeekMoE.
- **Total Parameters**: 671B; **Active Parameters per Token**: 37B.
- **Features**: Efficient inference through selective expert activation; supports chat functionalities.
- **Context Length**: Up to 64K tokens.

#### b. **DeepSeek-Reasoner (R1)**
- **Architecture**: MoE with reinforcement learning enhancements.
- **Total Parameters**: 671B; **Active Parameters per Token**: 37B.
- **Features**: Optimized for complex reasoning tasks; open-source and cost-effective.
- **Context Length**: Up to 64K tokens.

---

### 2. **Meta's Llama 4 Models**
- The Llama4 model has been the subject of much speculation, but its actual performance can only be determined through testing.
- For this evaluation, we utilized Together AI's API interface as our testing server.

#### a. **Llama 4-Maverick**
- **Architecture**: MoE with 128 experts.
- **Total Parameters**: ~400B; **Active Parameters per Token**: 17B.
- **Features**: Multimodal capabilities; excels in reasoning and coding tasks.
- **Context Length**: Up to 1M tokens.

#### b. **Llama 4-Scout**
- **Architecture**: MoE with 16 experts.
- **Total Parameters**: ~109B; **Active Parameters per Token**: 17B.
- **Features**: Efficient inference; supports multilingual and multimodal inputs.
- **Context Length**: Up to 10M tokens.

---

### 3. **Qwen**
- The Qwen coder model demonstrates the potential of small models in code generation.
- We tested it on both Groq and Together AI servers, with slight variations in results.

#### **Qwen2.5-coder-32B-Instruct**
- **Architecture**: Transformer-based model optimized for code generation.
- **Total Parameters**: 32B.
- **Features**: State-of-the-art performance on code generation benchmarks; competitive with GPT-4o.

---

### 4. **DeepCoder**
- DeepCoder-14B-Preview is a code reasoning LLM fine-tuned from DeepSeek-R1-Distilled-Qwen-14B using distributed reinforcement learning (RL) to scale up to long context length
- Currently, no cloud service provider offers API services for this model, so it can only be run locally on an NVIDIA RTX 4090 GPU. To test this model, we invested significant time configuring ollama, llama.cpp, and vllm. Ultimately, only FP8 quantization allowed us to complete the entire test within an acceptable timeframe. However, the test results were inconsistent, possibly due to configuration issues. I plan to revisit and reconfigure the setup when available.

#### **DeepCoder-14B-Preview-fp8**
- **Architecture**: Transformer-based model designed for code-related tasks.
- **Total Parameters**: 14B
- **Features**: Utilizes FP8 precision for efficient inference; tailored for code generation and reasoning.

---

## Testing Environment - EvalPlus Project

- EvalPlus is an advanced evaluation framework designed to enhance the assessment of Large Language Models (LLMs) in code generation tasks. Key features of EvalPlus include:
- EvalPlus support multiple backends, openai, vllm and etc.
```bash
export OPENAI_API_KEY="{KEY}" # https://platform.deepseek.com/api_keys

evalplus.evaluate --model "deepseek-chat" --dataset humaneval --base-url https://api.deepseek.com --backend openai --greedy

evalplus.evaluate --model "deepseek-reasoner" --dataset humaneval --base-url https://api.deepseek.com --backend openai --greedy

evalplus.evaluate --model "qwen-2.5-coder-32b" --dataset humaneval --base-url https://api.groq.com/openai/v1 --backend openai --greedy

evalplus.evaluate --model "Qwen/Qwen2.5-Coder-32B-Instruct" --dataset humaneval --base-url https://api.together.xyz/v1 --backend openai --greed
```

## Results
| Model | API Server | HumanEval(pass@1) | HumanEval+(extra tests pass@1) | Duration |
| --- | --- | --- | --- | --- |
| DeepSeek-Chat | DeepSeek | 0.939 | 0.890 | 1:11:35 |
| DeepSeek-Reasoner | DeepSeek | 0.976 | 0.921 | 5:42:18 |
| llama4-maverick | Together AI | 0.872 | 0.811 | 0:10:37 |
| llama4-scout | Together AI | 0.823 | 0.768 | 0:13:24 |
| llama3-3.3-70B-Instruct-Turbo | Together AI | 0.841 | 0.774 | 0:06:05 |
| Qwen-2.5-Coder-32B-Instruct | Groq | 0.927 | 0.878 | 0:11:54 |
| Qwen-2.5-Coder-32B-Instruct | Together AI | 0.902 | 0.860 | 0:11:38 |
| DeepCoder-14B-Preview-fp8(*) | 4090 vllm | < 0.5 | < 0.5 | 0:47:57 |
