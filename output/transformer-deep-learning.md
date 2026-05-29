---
title: "Transformer (deep learning)"
source_url: "https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)"
source_type: wikipedia
upload_date: 2026-05-20
extraction_date: 2026-05-29
lang: "en"
tags: [deep learning, natural language processing]
---

# Transformer (deep learning)

> **Summary:** Transformer is a family of artificial neural network architectures based on multi-head attention mechanism

Key concepts: [[multi-head attention]], [[word embedding]]

## Article

In deep learning, the transformer is a family of artificial neural network architectures based on the multi-head attention mechanism, in which text is converted to numerical representations called tokens, and each token is converted into a vector via lookup from a word embedding table. At each layer, each token is then contextualized within the scope of the context window with other (unmasked) tokens via a parallel multi-head attention mechanism, allowing the signal for key tokens to be amplified and less important tokens to be diminished. Because self-attention alone is permutation-invariant, transformers inject positional information, typically through positional encodings or learned positional embeddings, so token order can affect the output.
