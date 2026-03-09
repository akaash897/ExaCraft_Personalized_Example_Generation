"""
Subject Tag Metadata Module
Defines semantic subject tags used to categorize educational examples.
"""

SUBJECT_TAG_METADATA = {
    "algebraic_manipulation": {
        "description": "Rearranging and simplifying algebraic expressions",
        "domain": "mathematics"
    },
    "calculus_derivatives": {
        "description": "Differentiation, rates of change, and derivative rules",
        "domain": "mathematics"
    },
    "calculus_integrals": {
        "description": "Integration, antiderivatives, and area under curves",
        "domain": "mathematics"
    },
    "linear_algebra": {
        "description": "Vectors, matrices, linear transformations, and eigenvalues",
        "domain": "mathematics"
    },
    "probability_statistics": {
        "description": "Probability theory, distributions, and statistical inference",
        "domain": "mathematics"
    },
    "programming_loops": {
        "description": "Iteration constructs: for loops, while loops, recursion",
        "domain": "computer_science"
    },
    "programming_functions": {
        "description": "Function definition, parameters, return values, scope",
        "domain": "computer_science"
    },
    "data_structures": {
        "description": "Arrays, lists, trees, graphs, stacks, queues, hash maps",
        "domain": "computer_science"
    },
    "algorithms": {
        "description": "Sorting, searching, dynamic programming, graph algorithms",
        "domain": "computer_science"
    },
    "object_oriented_programming": {
        "description": "Classes, objects, inheritance, polymorphism, encapsulation",
        "domain": "computer_science"
    },
    "physics_mechanics": {
        "description": "Newton's laws, kinematics, energy, momentum, forces",
        "domain": "physics"
    },
    "physics_electromagnetism": {
        "description": "Electric fields, magnetic fields, circuits, waves",
        "domain": "physics"
    },
    "chemistry_reactions": {
        "description": "Chemical reactions, stoichiometry, balancing equations, kinetics",
        "domain": "chemistry"
    },
    "chemistry_bonding": {
        "description": "Ionic, covalent, metallic bonds, molecular structure",
        "domain": "chemistry"
    },
    "biology_cell": {
        "description": "Cell structure, organelles, cell division, cellular processes",
        "domain": "biology"
    },
    "biology_genetics": {
        "description": "DNA, genes, heredity, mutations, genetic variation",
        "domain": "biology"
    },
    "economics_microeconomics": {
        "description": "Supply and demand, market equilibrium, consumer behavior",
        "domain": "economics"
    },
    "economics_macroeconomics": {
        "description": "GDP, inflation, monetary policy, fiscal policy, trade",
        "domain": "economics"
    },
    "language_grammar": {
        "description": "Sentence structure, parts of speech, syntax, punctuation",
        "domain": "language"
    },
    "language_writing": {
        "description": "Essay structure, argumentation, rhetoric, style",
        "domain": "language"
    },
    "history_events": {
        "description": "Historical events, causes, consequences, timelines",
        "domain": "humanities"
    },
    "philosophy_logic": {
        "description": "Logical reasoning, fallacies, argumentation, syllogisms",
        "domain": "humanities"
    },
    "machine_learning": {
        "description": "ML models, training, feature engineering, evaluation",
        "domain": "computer_science"
    },
    "general_concept": {
        "description": "General educational concept not fitting other tags",
        "domain": "general"
    }
}


def load_subject_tag_metadata() -> dict:
    """Return the full subject tag metadata dictionary."""
    return SUBJECT_TAG_METADATA
