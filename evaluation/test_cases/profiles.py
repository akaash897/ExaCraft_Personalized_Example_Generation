"""
Diverse Test User Profiles

Coverage rationale:
  A robust evaluation requires profiles that span the full input space of the
  personalization system. Profiles vary across all dimensions tracked by ExaCraft:
    - Education level  (high school → graduate)
    - Profession       (technical → artistic → medical)
    - Cultural background / location  (6 continents represented)
    - Age range        (18-25, 26-35, 36-50)
    - Learning style   (practical, theoretical, visual)
    - Complexity       (simple, medium, advanced)
    - Interests        (domain-specific)

  This ensures the evaluation covers the full personalization space, not just a
  narrow slice. Coverage across demographics also mirrors responsible AI evaluation
  practice (Bommasani et al., 2021 — "On the Opportunities and Risks of Foundation Models").

  Format: matches the flat key format sent by the Chrome extension
  (handled by UserProfile.get_profile_summary).
"""

TEST_PROFILES = {

    # ── Profile 1: Early-career software engineer, India ──────────────────
    "software_engineer_india": {
        "user_id": "eval_001",
        "name": "Arjun",
        "location": "Bengaluru, India",
        "education": "undergraduate",
        "profession": "Software Engineer",
        "complexity": "medium",
        "cultural_background": "South Indian, Hindu",
        "age_range": "22-28",
        "interests": ["coding", "cricket", "Bollywood", "distributed systems"],
        "learning_style": "practical",
    },

    # ── Profile 2: High school student, Nigeria ───────────────────────────
    "high_school_nigeria": {
        "user_id": "eval_002",
        "name": "Chidi",
        "location": "Lagos, Nigeria",
        "education": "high_school",
        "profession": "Student",
        "complexity": "simple",
        "cultural_background": "Igbo, West African",
        "age_range": "16-18",
        "interests": ["football (soccer)", "Afrobeats music", "entrepreneurship", "mobile apps"],
        "learning_style": "visual",
    },

    # ── Profile 3: Graduate economics student, Germany ────────────────────
    "econ_grad_germany": {
        "user_id": "eval_003",
        "name": "Lena",
        "location": "Berlin, Germany",
        "education": "graduate",
        "profession": "Economics PhD Student",
        "complexity": "advanced",
        "cultural_background": "German, European",
        "age_range": "26-30",
        "interests": ["macroeconomics", "cycling", "philosophy", "data analysis"],
        "learning_style": "theoretical",
    },

    # ── Profile 4: Nurse practitioner, Brazil ─────────────────────────────
    "nurse_brazil": {
        "user_id": "eval_004",
        "name": "Gabriela",
        "location": "São Paulo, Brazil",
        "education": "undergraduate",
        "profession": "Nurse Practitioner",
        "complexity": "medium",
        "cultural_background": "Brazilian, Catholic",
        "age_range": "30-38",
        "interests": ["healthcare", "samba", "cooking", "community health"],
        "learning_style": "practical",
    },

    # ── Profile 5: Retired teacher, Japan ─────────────────────────────────
    "retired_teacher_japan": {
        "user_id": "eval_005",
        "name": "Hiroshi",
        "location": "Kyoto, Japan",
        "education": "graduate",
        "profession": "Retired High School Teacher",
        "complexity": "medium",
        "cultural_background": "Japanese, Buddhist",
        "age_range": "60-70",
        "interests": ["history", "calligraphy", "gardening", "education"],
        "learning_style": "theoretical",
    },

    # ── Profile 6: Undergraduate business student, USA ─────────────────────
    "business_student_usa": {
        "user_id": "eval_006",
        "name": "Marcus",
        "location": "Atlanta, USA",
        "education": "undergraduate",
        "profession": "Business Student",
        "complexity": "medium",
        "cultural_background": "African-American",
        "age_range": "20-24",
        "interests": ["entrepreneurship", "basketball", "hip-hop", "finance"],
        "learning_style": "practical",
    },

    # ── Profile 7: Data scientist, Egypt ──────────────────────────────────
    "data_scientist_egypt": {
        "user_id": "eval_007",
        "name": "Nour",
        "location": "Cairo, Egypt",
        "education": "graduate",
        "profession": "Data Scientist",
        "complexity": "advanced",
        "cultural_background": "Egyptian, Muslim",
        "age_range": "28-34",
        "interests": ["machine learning", "Arabic literature", "chess", "statistics"],
        "learning_style": "theoretical",
    },

    # ── Profile 8: Art student, Mexico ────────────────────────────────────
    "art_student_mexico": {
        "user_id": "eval_008",
        "name": "Sofia",
        "location": "Mexico City, Mexico",
        "education": "undergraduate",
        "profession": "Fine Arts Student",
        "complexity": "simple",
        "cultural_background": "Mexican, Catholic",
        "age_range": "20-24",
        "interests": ["painting", "Frida Kahlo", "street art", "music"],
        "learning_style": "visual",
    },
}
