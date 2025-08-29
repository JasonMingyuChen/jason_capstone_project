from utils.rubric_parser import parse_rubric

# Define the rubric data
raw_rubric = [
    {
        "id": "_5507",
        "points": 25.0,
        "description": "Critical Thinking & Argumentation (25 pts)",
        "long_description": "Thesis Quality (5 pts)<br/>\r\nPresents a clear, insightful, and arguable thesis that guides the essay<br/>\r\nAnalytical Depth (10 pts)<br/>\r\nDemonstrates deep analysis of financial literacy's impact using reasoning and economic principles<br/>\r\nCounterarguments (5 pts)<br/>\r\nAcknowledges alternative perspectives and refutes them logically<br/>\r\nOriginal Insight (5 pts)<br/>\r\nShows independent thought or creative synthesis of ideas",
        "criterion_use_range": True,
        "ratings": [
            {"id": "blank", "points": 25.0, "description": "Excellent", "long_description": ""},
            {"id": "_7863", "points": 20.0, "description": "Good", "long_description": ""},
            {"id": "_6978", "points": 15.0, "description": "Marginal", "long_description": ""},
            {"id": "blank_2", "points": 10.0, "description": "Poor", "long_description": ""}
        ]
    },
    {
        "id": "113_4577",
        "points": 20.0,
        "description": "Structure, Organization & Flow (20 pts)",
        "long_description": "Logical Progression (8 pts)<br/>\r\nIdeas are ordered logically and transitions guide the reader<br/>\r\nEffective Paragraphing (6 pts)<br/>\r\nEach paragraph has a clear focus and supports the thesis<br/>\r\nUse of Headings/Subsections (6 pts)<br/>\r\nOrganizes complex topics with visual clarity",
        "criterion_use_range": True,
        "ratings": [
            {"id": "113_2312", "points": 20.0, "description": "Excellent", "long_description": ""},
            {"id": "113_4453", "points": 15.0, "description": "Good", "long_description": ""},
            {"id": "113_5994", "points": 10.0, "description": "Marginal", "long_description": ""},
            {"id": "113_5929", "points": 5.0, "description": "Poor", "long_description": ""}
        ]
    },
    {
        "id": "113_2869",
        "points": 20.0,
        "description": "Use of Data, Evidence & Examples (20 pts)",
        "long_description": "Data Integration (8 pts)<br/>\r\nEffectively incorporates data to support arguments<br/>\r\nEvidence Quality (6 pts)<br/>\r\nUses credible, relevant examples and scholarly references<br/>\r\nInterpretation of Data (6 pts)<br/>\r\nDemonstrates understanding of the implications of data, not just mentions",
        "criterion_use_range": True,
        "ratings": [
            {"id": "113_4257", "points": 20.0, "description": "Excellent", "long_description": ""},
            {"id": "113_8797", "points": 15.0, "description": "Good", "long_description": ""},
            {"id": "113_5095", "points": 10.0, "description": "Marginal", "long_description": ""},
            {"id": "113_480", "points": 5.0, "description": "Poor", "long_description": ""}
        ]
    },
    {
        "id": "113_7358",
        "points": 15.0,
        "description": "Language, Style & Tone (15 pts)",
        "long_description": "Academic Voice (5 pts)<br/>\r\nMaintains a formal, objective, and academic tone<br/>\r\nLexical Variety (5 pts)<br/>\r\nEmploys diverse and appropriate vocabulary, including financial terminology<br/>\r\nSentence Fluency (5 pts)<br/>\r\nSentences vary in length/structure and read smoothly",
        "criterion_use_range": True,
        "ratings": [
            {"id": "113_8943", "points": 15.0, "description": "Excellent", "long_description": ""},
            {"id": "113_4766", "points": 11.25, "description": "Good", "long_description": ""},
            {"id": "113_91", "points": 7.5, "description": "Marginal", "long_description": ""},
            {"id": "113_3247", "points": 3.75, "description": "Poor", "long_description": ""}
        ]
    },
    {
        "id": "113_9759",
        "points": 10.0,
        "description": "Grammar, Mechanics & Conventions (10 pts)",
        "long_description": "Grammar & Syntax (4 pts)<br/>\r\nProper use of tenses, clauses, and sentence construction<br/>\r\nPunctuation & Spelling (3 pts)<br/>\r\nMinimal to no mechanical errors<br/>\r\nClarity (3 pts)<br/>\r\nSentences convey precise meaning without ambiguity",
        "criterion_use_range": True,
        "ratings": [
            {"id": "113_5967", "points": 10.0, "description": "Excellent", "long_description": ""},
            {"id": "113_465", "points": 7.5, "description": "Good", "long_description": ""},
            {"id": "113_398", "points": 5.0, "description": "Marginal", "long_description": ""},
            {"id": "113_4002", "points": 2.5, "description": "Poor", "long_description": ""}
        ]
    },
    {
        "id": "113_5232",
        "points": 10.0,
        "description": "Citations & Formatting (10 pts)",
        "long_description": "Proper APA Style (4 pts)<br/>\r\nFollows APA 7 formatting for in-text and reference citations<br/>\r\nReference Use (3 pts)<br/>\r\nMinimum of 3 credible sources cited appropriately<br/>\r\nDocument Formatting (3 pts)<br/>\r\nFollows standard formatting (title, spacing, font, margins)",
        "criterion_use_range": True,
        "ratings": [
            {"id": "113_9344", "points": 10.0, "description": "Excellent", "long_description": ""},
            {"id": "113_9179", "points": 7.5, "description": "Good", "long_description": ""},
            {"id": "113_8187", "points": 5.0, "description": "Marginal", "long_description": ""},
            {"id": "113_1343", "points": 2.5, "description": "Poor", "long_description": ""}
        ]
    }
]

# Parse and print the rubric
print(parse_rubric(raw_rubric)) 