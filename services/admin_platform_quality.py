def city_quality_row(db, city, category=None):
    score = int(getattr(city, 'readiness_score', 0) or 0)
    return {
        'readiness_score': score,
        'stored_readiness_score': score,
        'primary_blocker': None,
        'blockers': {},
    }


def quality_summary(db, city_slug=None, region=None, category=None, severity=None):
    from models.city import City
    query = db.query(City)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    if region:
        query = query.filter(City.region == region)
    rows = []
    for city in query.order_by(City.name.asc()).limit(200).all():
        quality = city_quality_row(db, city, category=category)
        row = {
            'city_slug': city.slug,
            'city_name': city.name,
            'region': city.region,
            'readiness_score': quality['readiness_score'],
            'stored_readiness_score': quality['stored_readiness_score'],
            'places_total': 0,
            'review_universe_total': 0,
            'manual_review_total': 0,
            'auto_excluded_total': 0,
            'severity': 'ok',
            'blockers': quality['blockers'],
            'primary_blocker': None,
            'route_candidate_total': 0,
            'route_ready_total': 0,
            'route_blockers_total': 0,
            'card_ready_total': 0,
            'card_blockers_total': 0,
            'auto_enrichment_total': 0,
            'critical_manual_review_total': 0,
            'optional_gaps_total': 0,
            'not_applicable_total': 0,
            'critical_coverage': {'degraded': True},
        }
        rows.append(row)
    if severity:
        rows = [row for row in rows if row['severity'] == severity]
    return {'items': rows, 'total': len(rows), 'todo': []}
