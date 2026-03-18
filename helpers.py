def calculate_grade(score):

    grade = Grade.query.filter(
            Grade.min_score <= score,
            Grade.max_score >= score
            ).first()

    if grade:
        return grade.grade
    return "N/A"



