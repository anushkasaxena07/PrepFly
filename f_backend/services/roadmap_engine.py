"""
PrepFly Personalized Preparation Roadmap Engine
Decouples the Recommendation Engine (what to learn & why) from the Scheduling Engine
(when & how much to learn), enforces strict daily capacity capping, respects prerequisite DAGs,
and performs non-destructive adaptive recalculations with full version audit logging.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta, timezone
import json
import uuid
import logging

logger = logging.getLogger("prepfly.roadmap")

from local_supabase import get_supabase_client
from services.skill_taxonomy_service import (
    SkillTaxonomyService,
    SKILL_CATALOG,
    ROLE_REQUIREMENTS,
    CAT_DSA,
    CAT_CS,
    CAT_SYSTEM_DESIGN,
    CAT_INTERVIEW_SKILLS,
    CAT_ML,
    CAT_DEEP_LEARNING,
    CAT_NLP,
    CAT_GENAI,
    CAT_DATA_ENGINEERING,
    CAT_MLOPS
)
from services.skill_profiling_service import SkillProfilingService
from services.candidate_profile_service import CandidateProfileService


# Comprehensive Curated Content Catalog with rich learning objectives,
# real-world scenarios, and measurable completion criteria across all domains.
CURATED_CONTENT_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    # ── Mathematics & Statistics ──
    "math_linear_algebra": [
        {
            "title": "Matrix Decompositions: Eigenvalues, Eigenvectors & SVD",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive spectral decomposition for symmetric matrices, geometric meaning of eigenvectors, and Singular Value Decomposition (SVD) low-rank approximation.",
            "completion_criteria": "State analytical proof connecting SVD to covariance matrix eigenvectors in PCA.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/math/svd-eigen"}
        },
        {
            "title": "Vector Projections, Dot Products & Hyperplanes",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement orthogonal Gram-Schmidt projection and vector projection matrices from first principles.",
            "completion_criteria": "Verify orthogonality invariants (u_i . u_j = 0) within float precision tolerance.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "gram-schmidt-orthogonalization", "doc_url": "https://prepfly.io/curriculum/math/vector-projections"}
        }
    ],
    "math_probability_statistics": [
        {
            "title": "Probability Distributions, MLE & Bayesian Inference",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive Maximum Likelihood Estimation (MLE) for Gaussian/Bernoulli distributions and formulate Bayes' Theorem with conjugate priors.",
            "completion_criteria": "Derive analytical closed-form MLE solution for normal distribution mean and variance.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/math/mle-bayes"}
        },
        {
            "title": "Hypothesis Testing, p-values & Statistical Power Analysis",
            "activity_type": "PRACTICE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Formulate two-sample t-tests, calculate Type I (alpha) and Type II (beta) errors, and compute statistical power for A/B tests.",
            "completion_criteria": "Calculate required sample sizes for 80% statistical power under minimum detectable effect.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/math/hypothesis-testing"}
        }
    ],

    # ── Machine Learning ──
    "ml_python_libraries": [
        {
            "title": "NumPy Vectorization, Strides & Memory Layout",
            "activity_type": "LEARN",
            "difficulty": "Beginner",
            "estimated_minutes": 30,
            "learning_objective": "Master C-contiguous vs Fortran-contiguous array memory layout, broadcasting rules, and eliminating Python loops with vectorized ufuncs.",
            "completion_criteria": "Vectorize matrix distance computation achieving 50x speedup over nested Python loops.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/numpy-vectorization"}
        },
        {
            "title": "High-Performance Pandas Data Manipulation & GroupBy",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement efficient dataframe aggregations, multi-index slicing, memory reduction via Categorical types, and window transforms.",
            "completion_criteria": "Pass unit tests validating zero chained indexing warnings and memory footprint reduction.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "pandas-dataframe-transforms", "doc_url": "https://prepfly.io/curriculum/ml/pandas-mastery"}
        }
    ],
    "ml_model_development": [
        {
            "title": "Model Architecture Formulation & Objective Invariants",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Formulate mathematical loss invariants (Cross-Entropy, Focal Loss, Triplet Margin) and gradient step stability.",
            "completion_criteria": "Derive analytical gradients and explain vanishing/exploding bounds.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/model-formulation"}
        },
        {
            "title": "Custom PyTorch Training Loop & Checkpointing",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement an end-to-end PyTorch training/eval loop with mixed precision (AMP), gradient clipping, and state dictionary serialization.",
            "completion_criteria": "Zero memory leaks in GPU tensors; accurate epoch evaluation validation.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "pytorch-train-loop", "doc_url": "https://prepfly.io/curriculum/ml/training-loops"}
        }
    ],
    "ml_supervised_unsupervised": [
        {
            "title": "Supervised & Unsupervised Invariant Derivation",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Master bias-variance trade-offs, regularized loss bounds (L1/L2), and clustering centroids.",
            "completion_criteria": "State exact mathematical assumptions for linear vs tree vs kernel models.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/supervised-learning"}
        },
        {
            "title": "Gradient Boosted Trees & Feature Importance",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement tree building invariants (histogram splitting, leaf shrinkage) and compute SHAP values.",
            "completion_criteria": "Correct split decision logic under missing value inputs.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "xgboost-invariants", "doc_url": "https://prepfly.io/curriculum/ml/tree-models"}
        }
    ],
    "ml_model_evaluation": [
        {
            "title": "Cost-Sensitive Evaluation Metrics & Calibration",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Analyze Precision-Recall curves, ROC-AUC under extreme class imbalance, and Platt/Isotonic probability calibration.",
            "completion_criteria": "Compute Brier score and expected calibration error (ECE).",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/evaluation-metrics"}
        },
        {
            "title": "Leakage-Free Cross-Validation Pipeline",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement stratified group k-fold validation preventing temporal and identity target leakage.",
            "completion_criteria": "Zero data contamination between training fold transforms and validation folds.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "leak-free-cv", "doc_url": "https://prepfly.io/curriculum/ml/cross-validation"}
        }
    ],
    "ml_feature_engineering": [
        {
            "title": "High-Cardinality Embeddings & Feature Transforms",
            "activity_type": "PRACTICE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Design out-of-vocabulary hash tricks, target encoding with smoothing, and log/Box-Cox transforms.",
            "completion_criteria": "Deliver vectorized feature encoding without Python loop overhead.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/ml/feature-engineering"}
        }
    ],
    "ml_classical_algorithms": [
        {
            "title": "Linear & Logistic Regression Gradient Derivation & Regularization",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive binary cross-entropy loss gradients, handle numerical stability with log-sum-exp, and analyze L1 (Lasso) vs L2 (Ridge) shrinkage.",
            "completion_criteria": "Explain geometrically why L1 regularization produces sparse feature weights while L2 decays weights.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/linear-logistic-regression"}
        },
        {
            "title": "Support Vector Machine (SVM) Dual Formulation & Kernels",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Formulate soft-margin SVM quadratic programming, Karush-Kuhn-Tucker (KKT) conditions, and RBF kernel projection.",
            "completion_criteria": "Explain the role of support vectors in defining margin hyperplanes.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "svm-dual-margin", "doc_url": "https://prepfly.io/curriculum/ml/svm-kernels"}
        }
    ],
    "ml_tree_ensembles": [
        {
            "title": "CART Splitting Mathematics: Gini Impurity vs Entropy",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Calculate split gain invariants for classification (Gini, Information Gain) and regression (Variance Reduction).",
            "completion_criteria": "Compute exact numerical split point on continuous features using histogram binning.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/tree-splitting"}
        },
        {
            "title": "Gradient Boosted Decision Trees (XGBoost/LightGBM) Invariants",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Derive second-order Taylor expansion loss gradients, tree structure score, and shrinkage rate.",
            "completion_criteria": "Implement leaf weight formula w* = -G / (H + lambda) and verify regularization penalty.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "xgboost-taylor-loss", "doc_url": "https://prepfly.io/curriculum/ml/gradient-boosting"}
        }
    ],
    "ml_clustering_pca": [
        {
            "title": "PCA Eigendecomposition & Dimensionality Reduction",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive PCA projection via covariance matrix eigendecomposition and maximize variance along principal axes.",
            "completion_criteria": "Compute cumulative explained variance ratio and select optimal dimension cutoff.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml/pca-math"}
        },
        {
            "title": "K-Means Convergence & DBSCAN Density Clustering",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement K-Means Lloyd's algorithm with K-Means++ initialization and DBSCAN core/border/noise point classification.",
            "completion_criteria": "Identify non-convex clusters where K-Means fails but DBSCAN succeeds.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "kmeans-dbscan-clustering", "doc_url": "https://prepfly.io/curriculum/ml/clustering"}
        }
    ],

    # ── Deep Learning ─────────────────────────────────────────────────────────
    "dl_neural_networks": [
        {
            "title": "Backprop Math, Initialization & Normalization Layers",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive chain-rule backpropagation through Batch Normalization and Layer Normalization layers.",
            "completion_criteria": "Explain variance scaling under He vs Xavier initialization.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/dl/neural-nets"}
        },
        {
            "title": "Residual Block & Skip Connection Implementation",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Construct modular ResNet-style skip blocks handling dimension matching with 1x1 convolutions.",
            "completion_criteria": "Pass unit tests verifying identity gradient flow.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "resnet-block", "doc_url": "https://prepfly.io/curriculum/dl/skip-connections"}
        }
    ],
    "dl_transformers": [
        {
            "title": "Scaled Dot-Product & Multi-Head Self-Attention Math",
            "activity_type": "LEARN",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Derive Q, K, V tensor projections, O(N^2) memory footprint, causal masking, and softmax stabilization.",
            "completion_criteria": "Calculate exact KV-cache memory consumption in bytes for a 7B model.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/dl/transformers"}
        },
        {
            "title": "Vectorized Multi-Head Attention Implementation",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Code a clean, broadcasted PyTorch MultiHeadAttention module with causal masking and dropout.",
            "completion_criteria": "Match PyTorch native scaled_dot_product_attention output within 1e-5 numerical tolerance.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "mha-implementation", "doc_url": "https://prepfly.io/curriculum/dl/mha-coding"}
        }
    ],
    "dl_fine_tuning": [
        {
            "title": "Parameter-Efficient Fine-Tuning: LoRA & QLoRA Invariants",
            "activity_type": "LEARN",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Analyze low-rank matrix decomposition W + (B x A) * (alpha / r), 4-bit NormalFloat quantization, and memory savings.",
            "completion_criteria": "State exact parameter count reduction and target module selection trade-offs.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/dl/peft-lora"}
        },
        {
            "title": "Instruction SFT Data Formatting & Packed Sequences",
            "activity_type": "PRACTICE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Structure chat template tokenization with loss masking on prompt tokens and concatenated packed sequences.",
            "completion_criteria": "Zero loss computation on system/user prompts; correctly placed end-of-turn tokens.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/dl/sft-data"}
        }
    ],
    "dl_frameworks_pytorch_tensorflow": [
        {
            "title": "PyTorch Autograd Mechanics & Tensor Memory Lifecycle",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Master computation graph construction, backward hooks, in-place tensor mutations, and torch.no_grad() memory savings.",
            "completion_criteria": "Explain gradient accumulation and when to call optimizer.zero_grad(set_to_none=True).",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/dl/pytorch-autograd"}
        },
        {
            "title": "Custom PyTorch Layer & Mixed Precision Training Loop",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Build custom PyTorch nn.Module with learnable parameters, initialize with Kaiming normal, and train with GradScaler.",
            "completion_criteria": "Pass unit tests verifying forward pass numerical accuracy and zero gradient explosion.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "pytorch-custom-layer", "doc_url": "https://prepfly.io/curriculum/dl/custom-modules"}
        }
    ],
    "dl_computer_vision_cnn": [
        {
            "title": "Convolutional Arithmetic, Receptive Fields & Strides",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive output spatial dimensions and calculate effective receptive field depth across conv layers.",
            "completion_criteria": "Calculate parameter counts and FLOPs for 3x3 standard vs depthwise-separable convolutions.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/dl/cnn-arithmetic"}
        },
        {
            "title": "ResNet Residual Block & Skip Connection Architecture",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Implement bottleneck residual block (1x1 -> 3x3 -> 1x1) with identity shortcut projection.",
            "completion_criteria": "Verify gradient highway behavior ensuring non-vanishing gradients across deep stacks.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "resnet-bottleneck-block", "doc_url": "https://prepfly.io/curriculum/dl/resnet-architecture"}
        }
    ],

    # ── NLP & Generative AI ───────────────────────────────────────────────────
    "nlp_embeddings": [
        {
            "title": "Dense Vector Representations & Contrastive Learning",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Analyze bi-encoder vs cross-encoder architectures, InfoNCE loss, and cosine similarity metric spaces.",
            "completion_criteria": "Explain the speed-accuracy trade-off of bi-encoders vs rerankers.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/nlp/embeddings"}
        },
        {
            "title": "Approximate Nearest Neighbor (ANN) Indexing: HNSW vs IVF",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Implement hierarchical graph traversal or inverted file clustering for sub-linear vector search.",
            "completion_criteria": "Measure recall@k vs query latency trade-offs on high-dimensional vectors.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "ann-indexing", "doc_url": "https://prepfly.io/curriculum/nlp/vector-index"}
        }
    ],
    "genai_llm_fundamentals": [
        {
            "title": "Autoregressive Decoding Strategies & KV-Cache Management",
            "activity_type": "LEARN",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Master greedy decoding, beam search, temperature scaling, top-k, top-p (nucleus), and PagedAttention memory paging.",
            "completion_criteria": "Calculate throughput impact of KV cache memory fragmentation.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/genai/decoding"}
        },
        {
            "title": "RAG Architecture & Hallucination Mitigation Design",
            "activity_type": "SYSTEM_DESIGN_EXERCISE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Architect enterprise Retrieval-Augmented Generation: chunking, hybrid BM25 + dense search, cross-encoder reranking, and citation grounding.",
            "completion_criteria": "Produce component diagram covering ingestion, retrieval, reranking, and generation with latency SLAs.",
            "resource_payload": {"type": "SYSTEM_DESIGN", "scenario": "enterprise_rag", "doc_url": "https://prepfly.io/curriculum/genai/rag-design"}
        }
    ],
    "nlp_pipelines": [
        {
            "title": "Subword Tokenization (BPE, WordPiece) & Batching",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Derive byte-pair encoding merge tables, vocabulary size trade-offs, and attention mask padding strategies.",
            "completion_criteria": "Explain out-of-vocabulary character fallback and token boundary alignment.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/nlp/tokenization"}
        }
    ],

    # ── Data Engineering ──────────────────────────────────────────────────────
    "data_preprocessing": [
        {
            "title": "Large-Scale Data Cleaning & Missing Value Imputation",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Design robust data normalization, IQR outlier rejection, and domain-grounded median/KNN imputation.",
            "completion_criteria": "Formulate deterministic pipeline stages without look-ahead bias.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/data/preprocessing"}
        },
        {
            "title": "Vectorized Feature Transformation Pipeline",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Build high-throughput Pandas/Polars vectorized transformers with strict schema validation.",
            "completion_criteria": "Achieve 10x throughput improvement over row-by-row apply operations.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "vectorized-pipeline", "doc_url": "https://prepfly.io/curriculum/data/vectorized-transforms"}
        }
    ],
    "data_dataset_management": [
        {
            "title": "Columnar Storage Formats & Streaming Datasets",
            "activity_type": "PRACTICE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Configure Parquet dictionary encoding, snappy compression, and streaming iterable dataset loaders for out-of-core training.",
            "completion_criteria": "Prove O(1) memory footprint when streaming 100GB+ datasets.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/data/streaming-datasets"}
        }
    ],

    # ── MLOps & Productionization ─────────────────────────────────────────────
    "mlops_model_serving_apis": [
        {
            "title": "High-Throughput Model Serving: vLLM & Triton Architecture",
            "activity_type": "LEARN",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Master dynamic batching, continuous iteration batching, tensor parallelism, and CUDA graph execution.",
            "completion_criteria": "Explain the latency vs throughput trade-off under high concurrency.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/mlops/serving-architectures"}
        },
        {
            "title": "Asynchronous Real-Time Prediction API",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Build an asynchronous FastAPI service with request queue batching, health probes, and timeout circuit breakers.",
            "completion_criteria": "Handle 100 concurrent requests within p99 latency target < 50ms.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "fastapi-model-serving", "doc_url": "https://prepfly.io/curriculum/mlops/serving-apis"}
        }
    ],
    "mlops_model_deployment": [
        {
            "title": "Deployment Strategies: Canary, Blue-Green & Shadow Traffic",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Design automated traffic shifting, shadow validation against dark production requests, and instantaneous rollback criteria.",
            "completion_criteria": "Define automated metrics thresholds for rollback triggering.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/mlops/deployment-strategies"}
        }
    ],
    "mlops_monitoring_drift": [
        {
            "title": "Data Drift (KS-Test, PSI) & Concept Drift Detection",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Formulate Population Stability Index (PSI), Kolmogorov-Smirnov test, and Wasserstein distance for continuous feature distribution tracking.",
            "completion_criteria": "State exact threshold ranges for PSI (< 0.1 stable, > 0.2 significant shift).",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/mlops/drift-detection"}
        },
        {
            "title": "Telemetry & Prometheus Model Monitoring Ingestion",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Expose custom Prometheus metrics for prediction drift, confidence percentiles, and request latencies.",
            "completion_criteria": "Validate Prometheus scrape format and latency bucket histograms.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "prometheus-metrics", "doc_url": "https://prepfly.io/curriculum/mlops/prometheus"}
        }
    ],
    "mlops_automated_retraining": [
        {
            "title": "Continuous Training Triggers & Champion-Challenger Validation",
            "activity_type": "PRACTICE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Architect automated pipeline triggers based on data volume, drift thresholds, and offline champion/challenger evaluation gates.",
            "completion_criteria": "Define safety rules preventing degraded models from automated promotion.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/mlops/retraining"}
        }
    ],

    # ── System Design & Scalability ───────────────────────────────────────────
    "sys_scalability": [
        {
            "title": "Distributed Training Paradigms: DDP, FSDP & ZeRO",
            "activity_type": "LEARN",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Analyze Data Parallelism (Ring-AllReduce), Fully Sharded Data Parallel (FSDP), and ZeRO memory partitioning (Stage 1, 2, 3).",
            "completion_criteria": "Calculate GPU memory savings when sharding optimizer states vs gradients vs model weights.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/system-design/distributed-training"}
        },
        {
            "title": "Architecting Large-Scale ML Recommendation Infrastructure",
            "activity_type": "SYSTEM_DESIGN_EXERCISE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Design an end-to-end multi-stage recommendation system: candidate generation (ANN), scoring (deep ranking), and re-ranking under 100ms SLA.",
            "completion_criteria": "Deliver component diagram with throughput, cache hit ratio, and fault-tolerance fallbacks.",
            "resource_payload": {"type": "SYSTEM_DESIGN", "scenario": "ml_recommendation_system", "doc_url": "https://prepfly.io/curriculum/system-design/recommendation-engine"}
        }
    ],
    "sys_ml_system_design": [
        {
            "title": "Real-Time Recommendation & Two-Stage Ranking Architecture",
            "activity_type": "SYSTEM_DESIGN_EXERCISE",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Architect high-scale recommendation pipeline: candidate generation (ANN/HNSW), scoring (multi-task deep ranking), and diversity re-ranking under 50ms SLA.",
            "completion_criteria": "Produce system architecture diagram covering online feature store, embedding retrieval, and ranking cache.",
            "resource_payload": {"type": "SYSTEM_DESIGN", "scenario": "two_stage_recommendation", "doc_url": "https://prepfly.io/curriculum/ml-systems/recommendation-design"}
        },
        {
            "title": "Feature Store Synchronization & Offline-to-Online Skew Prevention",
            "activity_type": "LEARN",
            "difficulty": "Advanced",
            "estimated_minutes": 30,
            "learning_objective": "Design dual-storage feature stores (Redis for low-latency online inference, Parquet/S3 for offline training) with point-in-time joins.",
            "completion_criteria": "Demonstrate prevention of target leakage and data staleness in streaming features.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/ml-systems/feature-stores"}
        }
    ],
    "sys_rest_apis": [
        {
            "title": "Idempotency, Rate Limiting & Backpressure in ML Services",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Implement Token Bucket / Leaky Bucket algorithms and idempotency keys to safeguard GPU inference clusters from request storms.",
            "completion_criteria": "Address client retry storms using exponential backoff with jitter.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/system-design/rate-limiting"}
        }
    ],
    "sys_db_design": [
        {
            "title": "Vector Databases vs Relational/NoSQL Trade-Offs",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Compare Milvus/Pinecone/pgvector index persistence, memory residency, and hybrid metadata filtering strategies.",
            "completion_criteria": "Quantify query performance differences between pre-filtering and post-filtering.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/system-design/vector-db"}
        }
    ],

    # ── Foundational DSA (Relevant Sub-Patterns) ──────────────────────────────
    "dsa_arrays": [
        {
            "title": "Array Invariants, Two-Pointer Partitioning & Prefix Sums",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Easy",
            "estimated_minutes": 30,
            "learning_objective": "Master two-pointer sliding boundaries and prefix sum lookup arrays in O(1) space.",
            "completion_criteria": "Pass all tests with zero off-by-one errors.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "two-sum", "doc_url": "https://prepfly.io/curriculum/dsa/arrays"}
        }
    ],
    "dsa_hashing": [
        {
            "title": "Hash Table Collisions, Load Factor & Frequency Encoders",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Easy",
            "estimated_minutes": 30,
            "learning_objective": "Implement custom hash table with open addressing/chaining and build O(1) lookup vocabulary maps.",
            "completion_criteria": "Correct amortized complexity under high collision rates.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "group-anagrams", "doc_url": "https://prepfly.io/curriculum/dsa/hashing"}
        }
    ],
    "dsa_trees": [
        {
            "title": "Tree Traversals (BFS, DFS) & Binary Search Tree Validation",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Medium",
            "estimated_minutes": 30,
            "learning_objective": "Implement recursive and iterative BST validation with tight boundary conditions.",
            "completion_criteria": "Pass tests including integer MIN/MAX boundary cases.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "validate-bst", "doc_url": "https://prepfly.io/curriculum/dsa/trees"}
        }
    ],
    "dsa_graphs": [
        {
            "title": "Graph Traversal & Topological Sort (Kahn's Algorithm)",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Medium",
            "estimated_minutes": 30,
            "learning_objective": "Model dependency DAGs and detect cycles in task scheduling workflows.",
            "completion_criteria": "Correct topological order with cycle detection.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "course-schedule", "doc_url": "https://prepfly.io/curriculum/dsa/graphs"}
        }
    ],
    "dsa_dp": [
        {
            "title": "Dynamic Programming: Memoization vs Tabulation",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Medium",
            "estimated_minutes": 30,
            "learning_objective": "Formulate state transition recurrence relations and optimize memory from 2D matrix to 1D array.",
            "completion_criteria": "Prove optimal substructure and overlapping subproblems.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "coin-change", "doc_url": "https://prepfly.io/curriculum/dsa/dp"}
        }
    ],

    # ── CS Fundamentals ───────────────────────────────────────────────────────
    "cs_concurrency": [
        {
            "title": "Thread Synchronization, Mutexes & Worker Pools",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Master thread-safe queues, deadlock prevention conditions, and multi-process data loading.",
            "completion_criteria": "Demonstrate race condition prevention under concurrent producer-consumer loads.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/cs/concurrency"}
        }
    ],
    "cs_os": [
        {
            "title": "Virtual Memory, Paging & Process Scheduling",
            "activity_type": "LEARN",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Understand page tables, TLB caching, context switching overhead, and memory mapping.",
            "completion_criteria": "Explain page faults and dirty page flushing mechanisms.",
            "resource_payload": {"type": "THEORY_STUDY", "doc_url": "https://prepfly.io/curriculum/cs/operating-systems"}
        }
    ],
    "cs_sql": [
        {
            "title": "Complex Window Functions, Joins & Query Execution Plans",
            "activity_type": "CODING_CHALLENGE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Write analytical SQL with ROW_NUMBER, RANK, DENSE_RANK, and CTE partitioning.",
            "completion_criteria": "Eliminate redundant table scans using proper index hints.",
            "resource_payload": {"type": "CODING_PROBLEM", "problem_id": "window-functions", "doc_url": "https://prepfly.io/curriculum/cs/sql"}
        }
    ],

    # ── Soft & Behavioral Skills ──────────────────────────────────────────────
    "soft_star_framework": [
        {
            "title": "STAR Behavioral: Conflict Resolution & Technical Disagreement",
            "activity_type": "MOCK_INTERVIEW",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Deliver structured responses for navigating technical disagreements on model vs product trade-offs.",
            "completion_criteria": "Include concrete quantifiable business outcomes in the Result segment.",
            "resource_payload": {"type": "AVA_SIMULATION", "topic": "behavioral_star", "doc_url": "https://prepfly.io/curriculum/behavioral"}
        }
    ],
    "soft_problem_understanding": [
        {
            "title": "Clarifying Constraints & Disambiguating Problem Statements",
            "activity_type": "PRACTICE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Systematically ask questions regarding scale, throughput, error tolerance, and data availability.",
            "completion_criteria": "Identify at least 3 implicit edge conditions before beginning solution design.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/behavioral/problem-understanding"}
        }
    ],
    "soft_complexity_analysis": [
        {
            "title": "Asymptotic Time & Space Analysis Under Interview Pressure",
            "activity_type": "PRACTICE",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Quickly and verbally derive tight Big-O bounds and space complexities without hesitation.",
            "completion_criteria": "State tight upper bounds (Big-O) and lower bounds (Big-Omega) with reasoning.",
            "resource_payload": {"type": "PRACTICE_DRILL", "doc_url": "https://prepfly.io/curriculum/behavioral/complexity-analysis"}
        }
    ],
    "soft_communication": [
        {
            "title": "Verbal Trade-Off Analysis in Architecture Design",
            "activity_type": "MOCK_INTERVIEW",
            "difficulty": "Intermediate",
            "estimated_minutes": 30,
            "learning_objective": "Articulate design alternatives clearly, explaining why alternative X was rejected in favor of Y.",
            "completion_criteria": "Structured verbal presentation covering latency, cost, and maintainability.",
            "resource_payload": {"type": "AVA_SIMULATION", "topic": "verbal_tradeoffs", "doc_url": "https://prepfly.io/curriculum/behavioral"}
        }
    ]
}

# Alias mapping for backwards compatibility
CURATED_CONTENT_CATALOG["arrays_hashing"] = CURATED_CONTENT_CATALOG.get("dsa_arrays", [])
CURATED_CONTENT_CATALOG["linked_lists"] = CURATED_CONTENT_CATALOG.get("dsa_arrays", [])
CURATED_CONTENT_CATALOG["trees_graphs"] = CURATED_CONTENT_CATALOG.get("dsa_trees", [])
CURATED_CONTENT_CATALOG["dynamic_programming"] = CURATED_CONTENT_CATALOG.get("dsa_dp", [])
CURATED_CONTENT_CATALOG["high_level_system_design"] = CURATED_CONTENT_CATALOG.get("sys_scalability", [])
CURATED_CONTENT_CATALOG["databases_caching"] = CURATED_CONTENT_CATALOG.get("sys_db_design", [])
CURATED_CONTENT_CATALOG["communication"] = CURATED_CONTENT_CATALOG.get("soft_communication", [])


class RecommendationEngine:
    """Evaluates candidate performance gaps, active target job requirements, and calculates what to learn using a 5-Tier Priority Hierarchy."""

    W_SKILL_GAP = 0.35
    W_JOB_RELEVANCE = 0.30
    W_PREREQUISITE = 0.15
    W_WEAKNESS = 0.10
    W_URGENCY = 0.10

    # Tier Priority Multipliers enforcing strict 5-Tier Hierarchy
    TIER_MULTIPLIERS = {
        1: 1.35,  # Tier 1: Explicit Mandatory JD Skills (core responsibilities & mandatory requirements)
        2: 1.20,  # Tier 2: Explicit Preferred JD Skills (bonus & preferred qualifications)
        3: 1.05,  # Tier 3: Role-Specific Foundational Knowledge from Canonical Taxonomy
        4: 0.70,  # Tier 4: Interview-Relevant DSA & CS Fundamentals (calibrated by role relevance)
        5: 0.60   # Tier 5: Behavioral & Soft Interview Skills
    }

    @classmethod
    def compute_priority(
        cls,
        skill_id: str,
        proficiency: float,
        role_importance: float,
        prerequisite_depth: int,
        evidence_count: int,
        days_to_deadline: int,
        tier: int = 3
    ) -> Dict[str, Any]:
        """
        Deterministic 5-Tier Multi-Factor Priority Formula:
        Priority = min(100.0, TierMultiplier * (w1*SkillGap + w2*JobRelevance + w3*Prereq + w4*Weakness + w5*Urgency))
        """
        # 1. Skill Gap (0 to 1.0): larger gap = higher priority
        skill_gap = max(0.0, min(1.0, (100.0 - proficiency) / 100.0))

        # 2. Job Relevance (0 to 1.0): based on normalized target role weight / JD weight
        job_relevance = max(0.0, min(1.0, role_importance))

        # 3. Prerequisite Importance: foundation skills unlock downstream nodes
        prereq_importance = min(1.0, max(0.2, prerequisite_depth * 0.25))

        # 4. Assessment Weakness: low score with high evidence implies persistent difficulty
        if evidence_count >= 1:
            weakness = max(0.2, (100.0 - proficiency) / 100.0)
        else:
            weakness = 0.5  # unassessed baseline

        # 5. Deadline Urgency: as interview gets closer, core gap priority increases
        if days_to_deadline <= 7:
            urgency = 1.0
        elif days_to_deadline <= 14:
            urgency = 0.8
        elif days_to_deadline <= 30:
            urgency = 0.7
        else:
            urgency = 0.5

        # Base Composite Score
        composite = (
            (cls.W_SKILL_GAP * skill_gap) +
            (cls.W_JOB_RELEVANCE * job_relevance) +
            (cls.W_PREREQUISITE * prereq_importance) +
            (cls.W_WEAKNESS * weakness) +
            (cls.W_URGENCY * urgency)
        )

        tier_mult = cls.TIER_MULTIPLIERS.get(tier, 1.0)
        scaled_score = composite * tier_mult * 100.0
        priority_score = min(100.0, max(5.0, round(scaled_score, 1)))

        return {
            "priority_score": priority_score,
            "tier": tier,
            "tier_multiplier": tier_mult,
            "components": {
                "skill_gap": round(skill_gap, 2),
                "job_relevance": round(job_relevance, 2),
                "prerequisite_importance": round(prereq_importance, 2),
                "assessment_weakness": round(weakness, 2),
                "deadline_urgency": round(urgency, 2)
            }
        }

    @classmethod
    def get_recommendations(
        cls,
        user_id: str,
        job_id: Optional[str] = None,
        supabase_client=None
    ) -> List[Dict[str, Any]]:
        """
        Produces ordered recommendations based on candidate's active Job Description,
        the 5-Tier Priority Hierarchy, and candidate proficiency/confidence profiles.
        """
        supabase = supabase_client or get_supabase_client()
        profile = CandidateProfileService.get_profile(supabase, user_id) or {}
        raw_role = profile.get("target_role", "Software Development Engineer (General)")

        # 1. Inspect Active Target Job Description
        active_job = None
        if job_id:
            j_res = supabase.table("job_profiles").select("*").eq("id", job_id).execute()
            if j_res and j_res.data:
                active_job = j_res.data[0]
        else:
            j_res = supabase.table("job_profiles").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
            if j_res and j_res.data:
                active_job = j_res.data[0]
                job_id = active_job.get("id")

        # Refine target role from JD title if candidate role is generic SDE or empty
        if active_job and active_job.get("job_title"):
            inferred_role_key = SkillTaxonomyService.normalize_role(active_job.get("job_title", ""))
            if raw_role in ("Software Development Engineer (General)", "SDE / Software Engineer", "General", ""):
                raw_role = active_job.get("job_title")
            norm_role = inferred_role_key
        else:
            norm_role = SkillTaxonomyService.normalize_role(raw_role)

        # 2. Fetch Extracted Requirements for active job
        jd_requirements: Dict[str, Dict[str, Any]] = {}
        if job_id:
            req_res = supabase.table("job_requirements").select("*").eq("job_id", job_id).execute()
            for r in (req_res.data or []):
                sid = r.get("normalized_skill_id") or r.get("canonical_skill_id")
                if sid:
                    jd_requirements[sid] = r

        # 3. Calculate Days to Deadline / Planned Horizon
        days_to_deadline = profile.get("total_days") or profile.get("days_planned") or profile.get("preparation_duration_days", 30)
        target_date_str = profile.get("target_date")
        if target_date_str:
            try:
                t_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                diff = (t_date - datetime.now(timezone.utc).date()).days
                if diff > 0:
                    days_to_deadline = diff
            except Exception:
                pass
        days_to_deadline = max(1, int(days_to_deadline))

        skill_profiles = SkillProfilingService.get_candidate_profile(supabase, user_id)
        role_weights = SkillTaxonomyService.get_role_weights(norm_role)
        prereq_depths = cls._compute_prerequisite_depths()

        recommendations = []
        for sid, skill_info in SKILL_CATALOG.items():
            sp = skill_profiles.get(sid, {})
            prof = float(sp.get("proficiency", 0.0))
            ev_count = int(sp.get("evidence_count", 0))
            confidence = float(sp.get("confidence", 0.0 if ev_count == 0 else 0.5))

            # Check if skill originates explicitly from ingested JD
            jd_req = jd_requirements.get(sid)
            is_from_jd = bool(jd_req)

            # Determine Tier Classification
            if is_from_jd:
                is_req = jd_req.get("is_required", 1)
                req_t = jd_req.get("requirement_type", "")
                if is_req == 1 or "mandatory" in req_t or "core" in req_t:
                    tier = 1  # Tier 1: Explicit Mandatory JD Skill
                    role_imp = 1.0
                else:
                    tier = 2  # Tier 2: Explicit Preferred JD Skill
                    role_imp = 0.85
            else:
                cat = skill_info.get("category", "")
                role_imp = float(role_weights.get(sid, 0.20))

                if role_imp >= 0.70:
                    tier = 3  # Tier 3: Role-Specific Foundational Knowledge
                elif cat in (CAT_DSA, CAT_CS):
                    tier = 4  # Tier 4: Interview-Relevant DSA & CS Fundamentals
                elif cat == CAT_INTERVIEW_SKILLS:
                    tier = 5  # Tier 5: Behavioral & Soft Interview Skills
                else:
                    tier = 4

            # Filter out skills completely irrelevant to target role (< 0.25)
            # unless present in JD or explicitly selected in user focus areas
            user_focus = profile.get("focus_areas") or []
            cat = skill_info.get("category", "")
            if not is_from_jd and role_imp < 0.25 and not any(f.lower() in cat.lower() for f in user_focus):
                continue

            depth = prereq_depths.get(sid, 1)

            prio_res = cls.compute_priority(
                skill_id=sid,
                proficiency=prof,
                role_importance=role_imp,
                prerequisite_depth=depth,
                evidence_count=ev_count,
                days_to_deadline=days_to_deadline,
                tier=tier
            )

            # Diagnostic Probe: only unassessed skills with zero evidence require diagnostic calibration
            needs_diagnostic = (ev_count == 0)

            # Build Traceable Rationale
            if is_from_jd:
                evidence = jd_req.get("evidence_text", "")
                prefix = "[Mandatory Requirement]" if tier == 1 else "[Preferred Qualification]"
                rationale = f"{prefix} Extracted directly from job description: '{evidence[:120]}...'" if evidence else f"{prefix} Target requirement for {raw_role}."
            else:
                rationale = (
                    f"Core curriculum for {raw_role} (weight {int(role_imp * 100)}%). "
                    f"Proficiency {round(prof)}% leaves {round(100 - prof)}% room for mastery."
                )

            if ev_count > 0 and prof < 50.0:
                rationale += " [Critical Baseline Gap — Priority Remediation Scheduled in Days 1-3]"
            elif ev_count > 0 and prof >= 80.0:
                rationale += " [Mastered Baseline — Advanced Synthesis Challenge Scheduled]"
            elif needs_diagnostic:
                rationale += " [Unassessed Baseline - Diagnostic Assessment Recommended]"

            recommendations.append({
                "skill_id": sid,
                "name": skill_info.get("name", sid),
                "category": skill_info.get("category", "General"),
                "proficiency": prof,
                "confidence": confidence,
                "evidence_count": ev_count,
                "needs_diagnostic": needs_diagnostic,
                "role_importance": role_imp,
                "tier": tier,
                "is_from_jd": is_from_jd,
                "originating_requirement_id": jd_req.get("id") if jd_req else None,
                "jd_evidence": jd_req.get("evidence_text") if jd_req else None,
                "priority_score": prio_res["priority_score"],
                "components": prio_res["components"],
                "rationale": rationale
            })

        # Sort strictly: Tier ascending (Tier 1 first), then Priority Score descending
        recommendations.sort(key=lambda r: (r["tier"], -r["priority_score"]))
        return recommendations

    @staticmethod
    def _compute_prerequisite_depths() -> Dict[str, int]:
        """Calculates prerequisite depth for topological scheduling."""
        dag = SkillTaxonomyService.get_prerequisites_dag()
        depths = {}
        for sid in SKILL_CATALOG:
            dependents = [child for child, parents in dag.items() if sid in parents]
            depths[sid] = 1 + len(dependents)
        return depths


class SchedulingEngine:
    """Allocates prioritized learning activities into daily study schedules with strict capacity capping and prerequisite gating."""

    @classmethod
    def generate_schedule(
        cls,
        user_id: str,
        recommendations: List[Dict[str, Any]],
        profile: Dict[str, Any],
        preserved_activities: Optional[List[Dict[str, Any]]] = None,
        job_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Builds a daily activity schedule:
        - Daily budget = daily_minutes (or daily_study_hours * 60)
        - Strict capacity enforcement: sum(duration_minutes) <= daily_capacity_minutes for EVERY day
        - Prerequisite topological order respected (foundations before advanced applications)
        - Low confidence skills receive Diagnostic Assessment drills first
        - Mandatory JD skills appear in the early days of the schedule
        - Preserved completed/pinned activities are untouched
        """
        # Determine daily study minutes budget (e.g. 60m)
        daily_mins = profile.get("daily_minutes")
        if daily_mins:
            daily_capacity_minutes = max(30, int(daily_mins))
        else:
            daily_hours = float(profile.get("daily_study_hours", 1.0))
            daily_capacity_minutes = max(30, int(daily_hours * 60))

        # Determine total calendar duration days (e.g. 9 days, 14 days, 30 days)
        if profile.get("total_days"):
            total_days = max(1, int(profile.get("total_days")))
        elif profile.get("days_planned"):
            total_days = max(1, int(profile.get("days_planned")))
        else:
            target_date_str = profile.get("target_date")
            if target_date_str:
                try:
                    t_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                    diff_days = (t_date - datetime.now(timezone.utc).date()).days
                    total_days = max(1, diff_days)
                except Exception:
                    total_days = int(profile.get("preparation_duration_days", 30))
            else:
                total_days = int(profile.get("preparation_duration_days", 30))

        scheduled_activities: List[Dict[str, Any]] = []
        occupied_day_minutes: Dict[int, int] = {d: 0 for d in range(1, total_days + 1)}

        # 1. Incorporate Preserved Activities (Completed or Pinned)
        completed_skills = set()
        if preserved_activities:
            for act in preserved_activities:
                d = act.get("day_number", 1)
                dur = int(act.get("estimated_minutes", act.get("duration_minutes", 30)))
                occupied_day_minutes[d] = occupied_day_minutes.get(d, 0) + dur
                act_copy = dict(act)
                act_copy["activity_id"] = act_copy.get("activity_id") or act_copy.get("id")
                scheduled_activities.append(act_copy)
                if act.get("status") in ("completed", "COMPLETED"):
                    completed_skills.add(act.get("skill_id"))

        # 2. Build Ordered Activity Queue with Prerequisite Awareness & Diagnostic Routing
        activity_queue: List[Dict[str, Any]] = []
        dag = SkillTaxonomyService.get_prerequisites_dag()

        # Group recommendations by tier and sort within tier by Priority Score descending
        tier1_recs = sorted([r for r in recommendations if r.get("tier") == 1], key=lambda r: -r.get("priority_score", 0.0))
        tier2_recs = sorted([r for r in recommendations if r.get("tier") == 2], key=lambda r: -r.get("priority_score", 0.0))
        tier3_recs = sorted([r for r in recommendations if r.get("tier") == 3], key=lambda r: -r.get("priority_score", 0.0))
        other_recs = sorted([r for r in recommendations if r.get("tier") not in (1, 2, 3)], key=lambda r: -r.get("priority_score", 0.0))

        # Collect foundation prerequisites needed by Tier 1 & 2 skills
        needed_prereqs = set()
        for r in (tier1_recs + tier2_recs):
            for p in dag.get(r["skill_id"], []):
                needed_prereqs.add(p)

        ordered_recs = []
        seen_sids = set()

        # Step A: Foundational prerequisites for JD skills (e.g. math_linear_algebra, ml_python_libraries)
        for r in tier3_recs:
            if r["skill_id"] in needed_prereqs and r["skill_id"] not in seen_sids:
                ordered_recs.append(r)
                seen_sids.add(r["skill_id"])

        # Step B: Tier 1 Mandatory JD Skills
        for r in tier1_recs:
            if r["skill_id"] not in seen_sids:
                ordered_recs.append(r)
                seen_sids.add(r["skill_id"])

        # Step C: Tier 2 Preferred JD Skills
        for r in tier2_recs:
            if r["skill_id"] not in seen_sids:
                ordered_recs.append(r)
                seen_sids.add(r["skill_id"])

        # Step D: Remaining Tier 3 Role Foundations (Weakest skills first for early remediation)
        for r in tier3_recs:
            if r["skill_id"] not in seen_sids:
                ordered_recs.append(r)
                seen_sids.add(r["skill_id"])

        # Step E: Other skills (Interview, DSA, CS)
        for r in other_recs:
            if r["skill_id"] not in seen_sids:
                ordered_recs.append(r)
                seen_sids.add(r["skill_id"])

        # Generate activities for each recommended skill calibrated to candidate diagnostic proficiency
        for rec in ordered_recs:
            sid = rec["skill_id"]
            prio = rec["priority_score"]
            reason = rec.get("rationale", "")
            req_id = rec.get("originating_requirement_id")
            jd_ev = rec.get("jd_evidence")
            prof = float(rec.get("proficiency", 0.0))
            ev_count = int(rec.get("evidence_count", 0))

            # If skill needs diagnostic assessment and has not been completed yet, queue assessment drill first
            if rec.get("needs_diagnostic") and prof < 80.0 and sid not in completed_skills:
                activity_queue.append({
                    "skill_id": sid,
                    "skill_name": rec["name"],
                    "category": rec["category"],
                    "title": f"Diagnostic Baseline: {rec['name']}",
                    "description": f"Targeted baseline assessment to calibrate candidate proficiency in {rec['name']}.",
                    "activity_type": "ASSESSMENT",
                    "difficulty": "Intermediate",
                    "estimated_minutes": min(30, daily_capacity_minutes),
                    "learning_objective": f"Establish verified baseline competency in {rec['name']} prior to deep practice.",
                    "completion_criteria": "Complete diagnostic assessment to unlock customized practice drills.",
                    "priority": prio + 5.0,
                    "recommendation_reason": reason,
                    "originating_requirement_id": req_id,
                    "jd_evidence": jd_ev,
                    "resource_payload": {"type": "DIAGNOSTIC_ASSESSMENT", "skill_id": sid, "requirement_id": req_id}
                })

            curated_pool = CURATED_CONTENT_CATALOG.get(sid)
            if curated_pool:
                for item in curated_pool:
                    item_diff = item.get("difficulty", "Intermediate")
                    item_title = item["title"]
                    item_type = item["activity_type"]
                    # Calibrate curated activity dynamically to candidate diagnostic performance
                    if ev_count > 0 and prof < 50.0:
                        item_diff = "Beginner"
                        item_title = f"Remediation: {item['title']}"
                    elif prof >= 80.0:
                        item_diff = "Advanced"
                        item_title = f"Advanced: {item['title']}"

                    activity_queue.append({
                        "skill_id": sid,
                        "skill_name": rec["name"],
                        "category": rec["category"],
                        "title": item_title,
                        "description": item.get("learning_objective", ""),
                        "activity_type": item_type,
                        "difficulty": item_diff,
                        "estimated_minutes": min(item.get("estimated_minutes", 30), daily_capacity_minutes),
                        "learning_objective": item["learning_objective"],
                        "completion_criteria": item["completion_criteria"],
                        "priority": (prio + 15.0) if (ev_count > 0 and prof < 50.0) else prio,
                        "recommendation_reason": reason,
                        "originating_requirement_id": req_id,
                        "jd_evidence": jd_ev,
                        "resource_payload": item.get("resource_payload", {})
                    })
            else:
                # Dynamically calibrate title, difficulty, and type based on diagnostic score
                if ev_count > 0 and prof < 50.0:
                    act_title = f"Remediation & Core Foundations: {rec['name']}"
                    act_desc = f"Targeted remediation drill addressing baseline gaps identified in diagnostic assessment for {rec['name']}."
                    act_obj = f"Close foundational knowledge gaps in {rec['name']} identified during diagnostic assessment."
                    act_crit = "Pass guided remediation exercises and review core conceptual invariants."
                    act_diff = "Beginner"
                    act_type = "CODING_CHALLENGE"
                    act_prio = prio + 15.0  # Elevate priority so it lands in Days 1-3
                elif prof >= 80.0:
                    act_title = f"Advanced Production Synthesis: {rec['name']}"
                    act_desc = f"High-complexity production optimization and architectural stress synthesis in {rec['name']}."
                    act_obj = f"Solve non-trivial production failure modes, performance bottlenecks, and scale limits in {rec['name']}."
                    act_crit = "Pass high-throughput stress tests and explain architectural trade-offs."
                    act_diff = "Advanced"
                    act_type = "SYSTEM_DESIGN" if rec.get("category") in ("System Design", "Machine Learning & AI") else "CODING_CHALLENGE"
                    act_prio = max(5.0, prio - 10.0)  # Schedule in synthesis days
                else:
                    act_title = f"Applied Mastery Drill: {rec['name']}"
                    act_desc = f"Master core patterns, invariants, and edge cases in {rec['name']}."
                    act_obj = f"Solidify fundamental invariants in {rec['name']}."
                    act_crit = "Pass all tests and explain complexity bounds."
                    act_diff = "Intermediate"
                    act_type = "CODING_CHALLENGE"
                    act_prio = prio

                activity_queue.append({
                    "skill_id": sid,
                    "skill_name": rec["name"],
                    "category": rec["category"],
                    "title": act_title,
                    "description": act_desc,
                    "activity_type": act_type,
                    "difficulty": act_diff,
                    "estimated_minutes": min(30, daily_capacity_minutes),
                    "learning_objective": act_obj,
                    "completion_criteria": act_crit,
                    "priority": act_prio,
                    "recommendation_reason": reason,
                    "originating_requirement_id": req_id,
                    "jd_evidence": jd_ev,
                    "resource_payload": {"type": "GENERAL_DRILL", "skill_id": sid}
                })

        # 3. Schedule Activities into Daily Plan Respecting Strict Capacity
        current_day = 1
        scheduled_skills_by_day: Dict[int, Set[str]] = {d: set() for d in range(1, total_days + 1)}
        all_scheduled_skills: Set[str] = set()

        now_dt = datetime.now(timezone.utc)

        for item in activity_queue:
            dur = item["estimated_minutes"]
            sid = item["skill_id"]

            # Advance current_day if current day has no capacity for this activity
            while current_day <= total_days and (occupied_day_minutes[current_day] + dur) > daily_capacity_minutes:
                current_day += 1

            if current_day > total_days:
                break

            # Check if this day is a spaced repetition milestone (Day 7, 14, 21, 28)
            if total_days >= 14 and current_day in (7, 14, 21, 28) and len(scheduled_skills_by_day[current_day]) == 0 and len(all_scheduled_skills) >= 2:
                rev_sid = list(all_scheduled_skills)[0]
                rev_dur = min(30, daily_capacity_minutes)
                rev_id = f"act_{uuid.uuid4().hex[:12]}"
                due_date = (now_dt + timedelta(days=current_day)).strftime("%Y-%m-%d")

                scheduled_activities.append({
                    "id": rev_id,
                    "activity_id": rev_id,
                    "skill_id": rev_sid,
                    "day_number": current_day,
                    "order_in_day": 1,
                    "title": f"Spaced Retrieval Practice: {SKILL_CATALOG.get(rev_sid, {}).get('name', 'Core Concepts')}",
                    "description": "Rapid-fire recall drill reviewing previously introduced algorithmic invariants and architectural principles.",
                    "activity_type": "REVISION",
                    "difficulty": "Intermediate",
                    "estimated_minutes": rev_dur,
                    "learning_objective": "Reinforce long-term retention via active retrieval without notes.",
                    "completion_criteria": "Complete retrieval drill with >= 75% accuracy.",
                    "priority": 0.90,
                    "due_date": due_date,
                    "status": "pending",
                    "is_pinned": 0,
                    "recommendation_reason": "Spaced repetition drill to consolidate prior learning.",
                    "resource_payload": json.dumps({"type": "SPACED_REPETITION", "skill_id": rev_sid})
                })
                occupied_day_minutes[current_day] += rev_dur

                if (occupied_day_minutes[current_day] + dur) > daily_capacity_minutes:
                    current_day += 1
                    if current_day > total_days:
                        break

            # Schedule the activity
            act_id = f"act_{uuid.uuid4().hex[:12]}"
            due_date = (now_dt + timedelta(days=current_day)).strftime("%Y-%m-%d")
            order_in_day = sum(1 for a in scheduled_activities if a.get("day_number") == current_day) + 1

            payload_obj = item.get("resource_payload", {})
            if isinstance(payload_obj, dict):
                if item.get("originating_requirement_id"):
                    payload_obj["originating_requirement_id"] = item["originating_requirement_id"]
                if item.get("jd_evidence"):
                    payload_obj["jd_evidence"] = item["jd_evidence"]

            scheduled_activities.append({
                "id": act_id,
                "activity_id": act_id,
                "skill_id": sid,
                "day_number": current_day,
                "order_in_day": order_in_day,
                "title": item["title"],
                "description": item["description"],
                "activity_type": item["activity_type"],
                "difficulty": item["difficulty"],
                "estimated_minutes": dur,
                "learning_objective": item["learning_objective"],
                "completion_criteria": item["completion_criteria"],
                "priority": item["priority"],
                "due_date": due_date,
                "status": "pending",
                "is_pinned": 0,
                "recommendation_reason": item.get("recommendation_reason", ""),
                "resource_payload": json.dumps(payload_obj) if isinstance(payload_obj, dict) else payload_obj
            })
            occupied_day_minutes[current_day] += dur
            scheduled_skills_by_day[current_day].add(sid)
            all_scheduled_skills.add(sid)

        # 4. Capstone Day on Final Horizon (e.g. Day 9 or Day 30)
        if current_day < total_days or occupied_day_minutes[total_days] < daily_capacity_minutes:
            capstone_day = total_days
            remaining_cap = daily_capacity_minutes - occupied_day_minutes[capstone_day]
            if remaining_cap >= 30:
                act_id = f"act_{uuid.uuid4().hex[:12]}"
                due_date = (now_dt + timedelta(days=capstone_day)).strftime("%Y-%m-%d")
                order_in_day = sum(1 for a in scheduled_activities if a.get("day_number") == capstone_day) + 1

                scheduled_activities.append({
                    "id": act_id,
                    "activity_id": act_id,
                    "skill_id": "soft_communication",
                    "day_number": capstone_day,
                    "order_in_day": order_in_day,
                    "title": "Comprehensive Ava AI Mock Interview Simulation",
                    "description": "Multi-turn interactive technical simulation testing domain problem decomposition, live trade-off analysis, and communication.",
                    "activity_type": "MOCK_INTERVIEW",
                    "difficulty": "Advanced",
                    "estimated_minutes": min(60, remaining_cap),
                    "learning_objective": "Demonstrate complete interview readiness under real-time simulation conditions.",
                    "completion_criteria": "Score >= 75% overall readiness score across all competency pillars.",
                    "priority": 0.95,
                    "due_date": due_date,
                    "status": "pending",
                    "is_pinned": 0,
                    "recommendation_reason": "Final milestone preparation for target interview.",
                    "resource_payload": json.dumps({"type": "AVA_SIMULATION", "topic": "comprehensive_interview"})
                })
                occupied_day_minutes[capstone_day] += min(60, remaining_cap)

        # Sort strictly by day_number and order_in_day
        scheduled_activities.sort(key=lambda a: (a.get("day_number", 1), a.get("order_in_day", 1)))
        return scheduled_activities


class PersonalizedRoadmapEngine:
    """Master engine orchestrating recommendation, scheduling, persistence, and non-destructive recalculation."""

    @classmethod
    def get_or_create_roadmap(
        cls,
        user_id: str,
        job_id: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """Fetches active roadmap or generates a new one if none exists."""
        supabase = supabase_client or get_supabase_client()
        res = supabase.table("roadmaps").select("*").eq("user_id", user_id).execute()
        if res and res.data:
            rm = res.data[0]
            act_res = supabase.table("roadmap_activities").select("*").eq("roadmap_id", rm["id"]).order("day_number").execute()
            activities = act_res.data if (act_res and act_res.data) else []

            by_day: Dict[int, List[Dict[str, Any]]] = {}
            for a in activities:
                d = a.get("day_number", 1)
                if d not in by_day:
                    by_day[d] = []
                by_day[d].append({
                    **a,
                    "activity_id": a.get("activity_id") or a.get("id"),
                    "skill_name": (SkillTaxonomyService.get_skill(a.get("skill_id", "")) or {}).get("name", a.get("skill_id", "")),
                    "category": (SkillTaxonomyService.get_skill(a.get("skill_id", "")) or {}).get("category", "")
                })

            total_acts = len(activities)
            completed_acts = sum(1 for a in activities if a.get("status") in ("completed", "COMPLETED"))
            completion_pct = round((completed_acts / total_acts * 100)) if total_acts > 0 else 0

            return {
                **rm,
                "roadmap_id": rm["id"],
                "version": rm.get("current_version", 1),
                "activities": activities,
                "schedule": by_day,
                "total_activities": total_acts,
                "completed_activities": completed_acts,
                "completion_percentage": completion_pct
            }

        # Generate fresh roadmap
        return cls.recalculate_roadmap(user_id=user_id, job_id=job_id, change_reason="Initial Roadmap Initialization", supabase_client=supabase)

    @classmethod
    def recalculate_roadmap(
        cls,
        user_id: str,
        job_id: Optional[str] = None,
        change_reason: str = "Adaptive Recalculation",
        trigger_event: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Performs non-destructive roadmap recalculation:
        - Preserves completed and pinned activities
        - Consumes active target job_requirements
        - Recalculates remaining recommendations based on updated skill profiles and target role
        - Generates new version snapshot in roadmap_versions
        - Atomically updates roadmap_activities
        - Returns both flat activities list and grouped schedule dict
        """
        supabase = supabase_client or get_supabase_client()
        profile = CandidateProfileService.get_profile(supabase, user_id) or {}
        target_role = profile.get("target_role", "Software Development Engineer (General)")

        # 1. Fetch Existing Roadmap if available
        rm_res = supabase.table("roadmaps").select("*").eq("user_id", user_id).execute()
        existing_rm = rm_res.data[0] if (rm_res and rm_res.data) else None

        preserved_activities: List[Dict[str, Any]] = []
        roadmap_id = existing_rm["id"] if existing_rm else f"rm_{uuid.uuid4().hex[:12]}"
        next_version = (existing_rm.get("current_version", 0) + 1) if existing_rm else 1

        if existing_rm:
            act_res = supabase.table("roadmap_activities").select("*").eq("roadmap_id", roadmap_id).execute()
            all_existing = act_res.data if (act_res and act_res.data) else []
            # Strictly preserve completed and pinned
            preserved_activities = [
                a for a in all_existing
                if a.get("status") in ("completed", "COMPLETED") or a.get("is_pinned") in (1, True)
            ]

        # 2. Get Ordered Recommendations based on candidate gap priority & target job
        recommendations = RecommendationEngine.get_recommendations(user_id, job_id=job_id, supabase_client=supabase)

        # 3. Schedule Activities into Daily Plan with Strict Capacity Enforcement
        scheduled = SchedulingEngine.generate_schedule(
            user_id=user_id,
            recommendations=recommendations,
            profile=profile,
            preserved_activities=preserved_activities,
            job_id=job_id
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        total_acts = len(scheduled)
        completed_acts = sum(1 for a in scheduled if a.get("status") in ("completed", "COMPLETED"))
        completion_pct = round((completed_acts / total_acts * 100)) if total_acts > 0 else 0

        # 4. Upsert Master Roadmap Record
        roadmap_record = {
            "id": roadmap_id,
            "user_id": user_id,
            "target_role": target_role,
            "current_version": next_version,
            "status": "active",
            "total_activities": total_acts,
            "completed_activities": completed_acts,
            "completion_percentage": completion_pct,
            "updated_at": now_iso
        }

        if existing_rm:
            supabase.table("roadmaps").update(roadmap_record).eq("id", roadmap_id).execute()
        else:
            roadmap_record["created_at"] = now_iso
            supabase.table("roadmaps").insert(roadmap_record).execute()

        # 5. Clear Unpinned/Pending Activities and Insert New Schedule
        supabase.table("roadmap_activities").delete().eq("roadmap_id", roadmap_id).neq("status", "completed").neq("is_pinned", 1).execute()

        preserved_ids = {a.get("id") for a in preserved_activities if a.get("id")}

        for act in scheduled:
            if act.get("id") in preserved_ids:
                continue

            insert_row = {
                "id": act["id"],
                "roadmap_id": roadmap_id,
                "user_id": user_id,
                "skill_id": act["skill_id"],
                "day_number": act["day_number"],
                "order_in_day": act["order_in_day"],
                "title": act["title"],
                "description": act.get("description", ""),
                "activity_type": act["activity_type"],
                "difficulty": act["difficulty"],
                "estimated_minutes": act["estimated_minutes"],
                "learning_objective": act.get("learning_objective", ""),
                "completion_criteria": act.get("completion_criteria", ""),
                "priority": act.get("priority", 1.0),
                "due_date": act.get("due_date"),
                "status": act.get("status", "pending"),
                "is_pinned": int(act.get("is_pinned", 0)),
                "recommendation_reason": act.get("recommendation_reason", ""),
                "resource_payload": act.get("resource_payload") if isinstance(act.get("resource_payload"), str) else json.dumps(act.get("resource_payload", {})),
                "created_at": now_iso,
                "updated_at": now_iso
            }
            supabase.table("roadmap_activities").upsert(insert_row).execute()

        # 6. Snapshot in roadmap_versions
        version_snapshot = {
            "id": f"ver_{uuid.uuid4().hex[:12]}",
            "roadmap_id": roadmap_id,
            "version_number": next_version,
            "change_reason": change_reason,
            "trigger_event": trigger_event or "MANUAL_RECALCULATION",
            "snapshot_data": json.dumps({
                "target_role": target_role,
                "total_activities": total_acts,
                "completed_activities": completed_acts,
                "activities_count": len(scheduled)
            }),
            "created_at": now_iso
        }
        try:
            supabase.table("roadmap_versions").insert(version_snapshot).execute()
        except Exception:
            pass

        # 7. Format by-day schedule dictionary for response
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for a in scheduled:
            d = a.get("day_number", 1)
            if d not in by_day:
                by_day[d] = []
            by_day[d].append({
                **a,
                "activity_id": a.get("activity_id") or a.get("id"),
                "skill_name": (SkillTaxonomyService.get_skill(a.get("skill_id", "")) or {}).get("name", a.get("skill_id", "")),
                "category": (SkillTaxonomyService.get_skill(a.get("skill_id", "")) or {}).get("category", "")
            })

        return {
            **roadmap_record,
            "roadmap_id": roadmap_id,
            "version": next_version,
            "activities": scheduled,
            "schedule": by_day,
            "total_activities": total_acts,
            "completed_activities": completed_acts,
            "completion_percentage": completion_pct
        }

    @classmethod
    def generate_company_personalized_plan(
        cls,
        user_id: str,
        company_name: str,
        role: str = "Software Engineer",
        experience_level: str = "Fresher",
        target_date: Optional[str] = None,
        daily_minutes: int = 60,
        study_days: Optional[List[str]] = None,
        prep_style: str = "mixed",
        job_description: Optional[str] = None,
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Master orchestrator generating a complete, adaptive company-specific preparation plan
        combining Dimension A (Candidate Readiness) with Dimension B (Company Interview Intelligence).
        """
        from services.company_gap_service import CompanyCandidateGapService
        from services.company_intelligence_service import CompanyIntelligenceService
        from services.candidate_readiness_service import CandidateReadinessService

        supabase = supabase_client or get_supabase_client()
        clean_company = (company_name or "Target Company").strip()
        clean_role = (role or "Software Engineer").strip()
        clean_level = (experience_level or "Fresher").strip()
        daily_cap = max(30, int(daily_minutes or 60))

        # 1. Calculate preparation timeline
        today = datetime.now(timezone.utc).date()
        days_to_deadline = 30
        if target_date:
            try:
                t_dt = datetime.strptime(str(target_date).strip()[:10], "%Y-%m-%d").date()
                diff = (t_dt - today).days
                days_to_deadline = max(1, diff)
            except Exception:
                days_to_deadline = 30

        total_days = min(60, max(3, days_to_deadline))

        # 2. Execute Gap Analysis (Dimension A + Dimension B)
        gap_result = CompanyCandidateGapService.analyze_company_candidate_gaps(
            user_id=user_id,
            company_name=clean_company,
            role=clean_role,
            experience_level=clean_level,
            days_to_deadline=total_days,
            supabase_client=supabase
        )

        company_profile = CompanyIntelligenceService.get_company_intelligence(
            company_name=clean_company,
            role=clean_role,
            experience_level=clean_level
        )

        candidate_snapshot = CandidateReadinessService.get_candidate_readiness_snapshot(
            user_id=user_id,
            target_role=clean_role,
            supabase_client=supabase
        )

        # 3. Retrieve any preserved activities
        preserved_activities: List[Dict[str, Any]] = []
        rm_res = supabase.table("roadmaps").select("*").eq("user_id", user_id).execute()
        existing_rm = rm_res.data[0] if (rm_res and rm_res.data) else None
        roadmap_id = existing_rm["id"] if existing_rm else f"rm_{uuid.uuid4().hex[:12]}"
        next_version = (existing_rm.get("current_version", 0) + 1) if existing_rm else 1

        if existing_rm:
            act_res = supabase.table("roadmap_activities").select("*").eq("roadmap_id", roadmap_id).execute()
            all_existing = act_res.data if (act_res and act_res.data) else []
            preserved_activities = [
                a for a in all_existing
                if a.get("status") in ("completed", "COMPLETED") or a.get("is_pinned") in (1, True)
            ]

        # 4. Schedule Activities into Daily Plan with Strict Capacity Enforcement
        scheduled_activities: List[Dict[str, Any]] = []
        occupied_day_minutes: Dict[int, int] = {d: 0 for d in range(1, total_days + 1)}

        # Incorporate preserved
        completed_skills = set()
        for act in preserved_activities:
            d = min(total_days, max(1, act.get("day_number", 1)))
            dur = int(act.get("estimated_minutes", 30))
            occupied_day_minutes[d] = occupied_day_minutes.get(d, 0) + dur
            act_copy = dict(act)
            act_copy["activity_id"] = act_copy.get("activity_id") or act_copy.get("id")
            scheduled_activities.append(act_copy)
            if act.get("status") in ("completed", "COMPLETED"):
                completed_skills.add(act.get("skill_id"))

        # Build activity queue from prioritized gaps
        top_gaps = gap_result.get("gaps", [])
        rounds = company_profile.get("round_structure", [])

        # Distribute company rounds as mock interview checkpoints
        mock_days = {}
        if total_days >= 7:
            step_interval = max(3, total_days // max(1, len(rounds)))
            for idx, r in enumerate(rounds):
                day_target = min(total_days, (idx + 1) * step_interval)
                mock_days[day_target] = r

        act_idx = 1
        for day in range(1, total_days + 1):
            avail_today = daily_cap - occupied_day_minutes.get(day, 0)
            if avail_today < 20:
                continue

            # Check if this day is a dedicated Company Mock Round Checkpoint
            if day in mock_days and avail_today >= 45:
                round_info = mock_days[day]
                m_dur = min(avail_today, 45)
                act_id = f"act_{uuid.uuid4().hex[:10]}"
                scheduled_activities.append({
                    "id": act_id,
                    "activity_id": act_id,
                    "roadmap_id": roadmap_id,
                    "user_id": user_id,
                    "day_number": day,
                    "order_in_day": len([a for a in scheduled_activities if a.get("day_number") == day]) + 1,
                    "skill_id": "soft_behavioral_star" if "behavioral" in round_info["name"].lower() or "googliness" in round_info["name"].lower() else "dsa_graphs_bfs_dfs",
                    "title": f"Ava Mock: {clean_company} Round {round_info['round_number']} ({round_info['name']})",
                    "description": f"Simulated interview round tailored to {clean_company}'s evaluation rubrics and {round_info['focus']}.",
                    "activity_type": "MOCK_INTERVIEW",
                    "difficulty": "Medium-to-Hard" if "senior" in clean_level.lower() else "Medium",
                    "estimated_minutes": m_dur,
                    "learning_objective": f"Practice under realistic {clean_company} round format: {round_info['focus']}.",
                    "completion_criteria": f"Complete full 45-minute interactive interview with Ava and achieve >= 70% rubric score.",
                    "priority": 95.0,
                    "status": "pending",
                    "is_pinned": 0,
                    "company_relevance": 0.98,
                    "resource_payload": json.dumps({
                        "company": clean_company,
                        "round_name": round_info["name"],
                        "format": round_info.get("format", "Virtual 1-on-1"),
                        "interview_mode": "company_mock"
                    })
                })
                occupied_day_minutes[day] += m_dur
                avail_today -= m_dur

            # Fill remaining day budget with prioritized gap activities
            gap_candidates = [g for g in top_gaps if g["skill_id"] not in completed_skills]
            for gap in gap_candidates:
                if avail_today < 25:
                    break

                skill_id = gap["skill_id"]
                content_items = CURATED_CONTENT_CATALOG.get(skill_id, [])
                if not content_items:
                    continue

                for item in content_items:
                    dur = int(item.get("estimated_minutes", 30))
                    if dur <= avail_today:
                        act_id = f"act_{uuid.uuid4().hex[:10]}"
                        scheduled_activities.append({
                            "id": act_id,
                            "activity_id": act_id,
                            "roadmap_id": roadmap_id,
                            "user_id": user_id,
                            "day_number": day,
                            "order_in_day": len([a for a in scheduled_activities if a.get("day_number") == day]) + 1,
                            "skill_id": skill_id,
                            "title": f"[{clean_company} Prep] {item['title']}",
                            "description": f"Targeted preparation for {clean_company} {clean_role}: {item.get('learning_objective', '')}",
                            "activity_type": item.get("activity_type", "LEARN"),
                            "difficulty": item.get("difficulty", "Intermediate"),
                            "estimated_minutes": dur,
                            "learning_objective": item.get("learning_objective", ""),
                            "completion_criteria": item.get("completion_criteria", ""),
                            "priority": gap.get("priority_score", 80.0),
                            "status": "pending",
                            "is_pinned": 0,
                            "company_relevance": gap.get("company_relevance", 0.70),
                            "resource_payload": json.dumps(item.get("resource_payload", {}))
                        })
                        occupied_day_minutes[day] += dur
                        avail_today -= dur

        # 5. Save Roadmap and Activities
        now_iso = datetime.now(timezone.utc).isoformat()
        total_acts = len(scheduled_activities)
        completed_acts = sum(1 for a in scheduled_activities if a.get("status") in ("completed", "COMPLETED"))
        completion_pct = round((completed_acts / max(1, total_acts)) * 100)

        roadmap_record = {
            "id": roadmap_id,
            "user_id": user_id,
            "target_role": clean_role,
            "current_version": next_version,
            "status": "active",
            "total_activities": total_acts,
            "completed_activities": completed_acts,
            "completion_percentage": completion_pct,
            "updated_at": now_iso
        }

        if existing_rm:
            supabase.table("roadmaps").update(roadmap_record).eq("id", roadmap_id).execute()
        else:
            roadmap_record["created_at"] = now_iso
            supabase.table("roadmaps").insert(roadmap_record).execute()

        # Update candidate profile target fields
        try:
            profile_update = {
                "target_company": clean_company,
                "target_role": clean_role,
                "experience_level": clean_level,
                "daily_minutes": daily_cap,
                "target_date": target_date or (today + timedelta(days=total_days)).isoformat(),
                "updated_at": now_iso
            }
            supabase.table("candidate_profiles").update(profile_update).eq("user_id", user_id).execute()
        except Exception:
            pass

        # Clear pending and insert updated schedule
        supabase.table("roadmap_activities").delete().eq("roadmap_id", roadmap_id).neq("status", "completed").neq("is_pinned", 1).execute()

        preserved_ids = {a.get("id") for a in preserved_activities if a.get("id")}
        for act in scheduled_activities:
            if act.get("id") in preserved_ids:
                continue
            insert_row = {
                "id": act["id"],
                "roadmap_id": roadmap_id,
                "user_id": user_id,
                "skill_id": act["skill_id"],
                "day_number": act["day_number"],
                "order_in_day": act["order_in_day"],
                "title": act["title"],
                "description": act.get("description", ""),
                "activity_type": act["activity_type"],
                "difficulty": act["difficulty"],
                "estimated_minutes": act["estimated_minutes"],
                "learning_objective": act.get("learning_objective", ""),
                "completion_criteria": act.get("completion_criteria", ""),
                "priority": act.get("priority", 1.0),
                "status": act.get("status", "pending"),
                "is_pinned": int(act.get("is_pinned", 0)),
                "resource_payload": act.get("resource_payload") if isinstance(act.get("resource_payload"), str) else json.dumps(act.get("resource_payload", {})),
                "created_at": now_iso,
                "updated_at": now_iso
            }
            try:
                supabase.table("roadmap_activities").insert(insert_row).execute()
            except Exception as e:
                logger.warning(f"Error inserting activity {act['id']}: {e}")

        # Format by-day schedule dictionary
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for a in scheduled_activities:
            d = a.get("day_number", 1)
            if d not in by_day:
                by_day[d] = []
            by_day[d].append({
                **a,
                "activity_id": a.get("activity_id") or a.get("id"),
                "skill_name": (SkillTaxonomyService.get_skill(a.get("skill_id", "")) or {}).get("name", a.get("skill_id", "")),
                "category": (SkillTaxonomyService.get_skill(a.get("skill_id", "")) or {}).get("category", "")
            })

        return {
            "success": True,
            "company_name": clean_company,
            "target_role": clean_role,
            "experience_level": clean_level,
            "target_date": target_date or (today + timedelta(days=total_days)).isoformat(),
            "daily_minutes": daily_cap,
            "total_days": total_days,
            "total_study_hours": round((total_days * daily_cap) / 60.0, 1),
            "company_intelligence": company_profile,
            "candidate_readiness": candidate_snapshot,
            "gap_analysis": gap_result,
            "roadmap": {
                **roadmap_record,
                "roadmap_id": roadmap_id,
                "version": next_version,
                "activities": scheduled_activities,
                "schedule": by_day,
                "total_activities": total_acts,
                "completed_activities": completed_acts,
                "completion_percentage": completion_pct
            },
            "tailored_question_bank": gap_result.get("tailored_question_bank", []),
            "generated_at": now_iso
        }
