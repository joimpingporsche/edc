flowchart TD
    INPUT([Input Documents\nPDFs / Text Files])
    INPUT --> PDF[pdf_to_text_and_tables.py\nPDF → Structured Text + Tables]

    PDF --> CHUNK

    subgraph PRE["Preprocessing"]
        CHUNK{Chunking Variant}
        CHUNK -->|v1 · Fixed-Window| V1[chunking_v1.py\nSentence / Char Windows]
        CHUNK -->|v2 · Adaptive-Section| V2[chunking_v2.py\nSection-aware Chunking]
    end

    V1 & V2 --> CHUNKS[(Text Chunks\nchunks.jsonl\nchunks_text.txt)]

    SCHEMA[(Target Schema\nschemas/*.csv\nrelation → definition)]

    subgraph EDCF["EDC Framework  ·  edc_framework.py"]
        CHUNKS --> OIE["① OIE  ·  extract.py\nOpen Information Extraction\nLLM extracts raw triplets"]
        OIE --> RTRIP["Raw Triplets\n⟨subject, relation, object⟩"]

        RTRIP --> DCGATE{"disable_dc?"}

        DCGATE -->|"No (default)"| SDEF["② Schema Definition  ·  schema_definition.py\nLLM defines each extracted relation"]
        SDEF --> RDEF[Relation Definitions\nrelation → description dict]
        RDEF --> SCAN["③ Schema Canonicalization  ·  schema_canonicalization.py\nEmbedder retrieves top-k candidates\nLLM verifies best match"]
        SCAN --> CTRIP[Canonical Triplets]

        DCGATE -->|Yes| CTRIP

        CTRIP --> TUFGATE{"Triple Utility\nFilter enabled?"}
        TUFGATE -->|Yes| TUF["④ Triple Utility Filter  ·  triple_utility_filter.py\nLLM removes non-schema-useful triplets"]
        TUFGATE -->|No| KGTRIP
        TUF --> KGTRIP[KG Triplets]

        KGTRIP --> REFGATE{"Refinement\nIterations > 0?"}
        REFGATE -->|No| DONE([Output KG\ncanon_kg_dedup.txt])
        REFGATE -->|"Yes → next iter"| EE["Entity Extraction  ·  entity_extraction.py\nLLM extracts + merges entities"]
        EE --> SR["Schema Retriever  ·  schema_retriever.py\nEmbedder retrieves relevant relations"]
        SR --> HINTS["Entity & Relation Hints\n(used for Refined OIE)"]
        HINTS --> OIE
    end

    SCHEMA --> SCAN
    SCHEMA --> SR

    subgraph EVAL["Evaluation  ·  evaluate/"]
        EV1[evaluate_ontology_compliance.py\nOntology alignment & compliance score]
        EV2[evaluation_script.py\nPrecision / Recall / F1]
        EV3[two_track_evaluation.py\nTwo-track evaluation]
    end

    DONE --> EV1 & EV2 & EV3

    classDef module fill:#dbeafe,stroke:#2563eb,color:#1e3a5f
    classDef data fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef gate fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef io fill:#f3e8ff,stroke:#7c3aed,color:#3b0764
    classDef eval fill:#ffe4e6,stroke:#e11d48,color:#881337

    class OIE,SDEF,SCAN,TUF,EE,SR,PDF,V1,V2 module
    class RTRIP,RDEF,CTRIP,KGTRIP,HINTS,CHUNKS,SCHEMA data
    class DCGATE,TUFGATE,REFGATE,CHUNK gate
    class INPUT,DONE io
    class EV1,EV2,EV3 eval