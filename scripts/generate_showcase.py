from datetime import datetime, timezone
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rv_winner_scout.domain.models import (
    ProductCandidate,
    RawAmazonProduct,
    VerifiedAmazonProduct,
    WalmartResearchResult,
    ProductOpportunity,
    RunHealthReport,
)
from rv_winner_scout.domain.scoring import RawDimensionScores, calculate_score_breakdown
from rv_winner_scout.domain.enums import (
    WalmartStatus,
    NewnessStatus,
    ExposureLevel,
    VerificationState,
    TrafficBenchmark,
    TrafficConfidence,
)
from rv_winner_scout.reporting.dashboard_generator import generate_executive_dashboard_html

def build_showcase():
    # 1. Soft Starter (The Client Benchmark Product)
    p1_raw = RawAmazonProduct(
        title='Soft Start for RV Air Conditioners Reduces Startup Current by up to 75%, Easy DIY Installation RV Soft Starter Compatible with Coleman, Dometic and Other Major Brands (115V)',
        url='https://www.amazon.com/dp/B0GYD3TVDV',
        asin='B0GYD3TVDV',
        displayed_price=89.99,
        image_url='https://m.media-amazon.com/images/I/61k1jYqS48L._AC_SL1500_.jpg',
        images=[
            'https://m.media-amazon.com/images/I/61k1jYqS48L._AC_SL1500_.jpg',
            'https://m.media-amazon.com/images/I/71u9Sg9zZ8L._AC_SL1500_.jpg',
            'https://m.media-amazon.com/images/I/61aW+B4j1iL._AC_SL1500_.jpg',
            'https://m.media-amazon.com/images/I/71kCg8Ff8uL._AC_SL1500_.jpg'
        ],
        bsr_rank='#1,420 in RV Air Conditioners & Accessories',
        category='RV Parts & Accessories',
        source_page_url='https://www.amazon.com/gp/new-releases/automotive/2258019011/'
    )
    p1_ver = VerifiedAmazonProduct(
        title=p1_raw.title,
        asin='B0GYD3TVDV',
        canonical_url='https://www.amazon.com/dp/B0GYD3TVDV',
        displayed_price=89.99,
        bsr=1420,
        bsr_rank=p1_raw.bsr_rank,
        images=p1_raw.images,
        bullet_points=[
            'Reduces AC inrush current by up to 75%',
            'Allows running 15K BTU AC on a small 2000W generator',
            'Easy DIY installation with plug-and-play color-coded wiring harness',
            'Extends RV air conditioning compressor lifespan'
        ],
        verification_state=VerificationState.VERIFIED
    )
    p1_scores = calculate_score_breakdown(
        raw=RawDimensionScores(
            facebook_discovery_potential=9.5,
            rv_facebook_exposure=9.2,
            rv_relevance=9.5,
            novelty_newness=8.5,
            problem_solving_power=9.8,
            visual_wow=7.5,
            space_convenience=8.0,
            impulse_click_potential=8.5,
            rv_audience_breadth=8.0,
        ),
        exposure_level=ExposureLevel.VERY_LOW,
        strong_didnt_know_existed=True
    )
    p1_cand = ProductCandidate(
        canonical_url='https://www.amazon.com/dp/B0GYD3TVDV',
        asin='B0GYD3TVDV',
        normalized_title=p1_raw.title.lower(),
        raw_product=p1_raw,
        verified_product=p1_ver,
        verification_state=VerificationState.VERIFIED,
        newness=NewnessStatus.NEW,
        exposure_level=ExposureLevel.VERY_LOW,
        scores=p1_scores,
        opportunity=ProductOpportunity(
            visual_hook='Side-by-side clamp meter comparison: Inrush amps drop from 48A down to 14A, proving you can run your RV AC on a portable 2000W generator.',
            facebook_angle='Share with RV boondocking & dry camping groups: Stop hauling a 4000W generator just to stay cool off-grid.',
            why_next_winner='Solves the #1 boondocking dilemma by cutting AC startup surge by 75%, allowing RV owners to run their rooftop AC on a small 2000W generator without tripping breakers.',
            why_fail='Requires basic DIY electrical wiring inside the rooftop AC cowling; non-DIYers may hesitate or require professional installation.',
            traffic_benchmark=TrafficBenchmark.P_25_50,
            confidence=TrafficConfidence.HIGH,
            exact_walmart_query='RV AC soft starter 115V'
        ),
        walmart=WalmartResearchResult(
            search_query_used='RV AC soft starter 115V',
            status=WalmartStatus.FOUND,
            displayed_price=94.50,
            url='https://www.walmart.com/search?q=RV+AC+soft+starter+115V'
        )
    )

    # 2. Camco Heated Drinking Water Hose
    p2_raw = RawAmazonProduct(
        title='Camco Heated Drinking Water Hose with Energy-Saving Thermostat (25FT x 5/8 Inch) - Freeze Protection Down to -20F',
        url='https://www.amazon.com/dp/B0DC8X7K2M',
        asin='B0DC8X7K2M',
        displayed_price=69.95,
        image_url='https://m.media-amazon.com/images/I/71Zp+kH76KL._AC_SL1500_.jpg',
        images=[
            'https://m.media-amazon.com/images/I/71Zp+kH76KL._AC_SL1500_.jpg',
            'https://m.media-amazon.com/images/I/71O0hD2l6LL._AC_SL1500_.jpg',
            'https://m.media-amazon.com/images/I/81fHwYp+YlL._AC_SL1500_.jpg'
        ],
        bsr_rank='#4,210 in RV Fresh Water Accessories',
        category='RV Parts & Accessories',
        source_page_url='https://www.amazon.com/gp/new-releases/automotive/2258019011/'
    )
    p2_ver = VerifiedAmazonProduct(
        title=p2_raw.title,
        asin='B0DC8X7K2M',
        canonical_url='https://www.amazon.com/dp/B0DC8X7K2M',
        displayed_price=69.95,
        bsr=4210,
        bsr_rank=p2_raw.bsr_rank,
        images=p2_raw.images,
        bullet_points=[
            'Self-regulating freeze protection down to -20F',
            'Drinking water safe NSF-61 certified',
            'Durable exterior jacket protects against freezing winter winds'
        ],
        verification_state=VerificationState.VERIFIED
    )
    p2_scores = calculate_score_breakdown(
        raw=RawDimensionScores(
            facebook_discovery_potential=8.5,
            rv_facebook_exposure=8.0,
            rv_relevance=9.5,
            novelty_newness=7.5,
            problem_solving_power=9.2,
            visual_wow=7.0,
            space_convenience=7.5,
            impulse_click_potential=8.5,
            rv_audience_breadth=8.5,
        ),
        exposure_level=ExposureLevel.VERY_LOW,
        strong_didnt_know_existed=False
    )
    p2_cand = ProductCandidate(
        canonical_url='https://www.amazon.com/dp/B0DC8X7K2M',
        asin='B0DC8X7K2M',
        normalized_title=p2_raw.title.lower(),
        raw_product=p2_raw,
        verified_product=p2_ver,
        verification_state=VerificationState.VERIFIED,
        newness=NewnessStatus.NEW,
        exposure_level=ExposureLevel.VERY_LOW,
        scores=p2_scores,
        opportunity=ProductOpportunity(
            visual_hook='Ice-cold freezing water test: Outdoor hose remains completely flowing and flexible while standard hoses freeze solid into ice pipes.',
            facebook_angle='Target winter RVers & snowbirds: Never wake up to frozen water pipes or busted valves in freezing campgrounds.',
            why_next_winner='Crucial freeze-protection down to -20F with energy-saving thermostat; essential winter RV survival gear with instant high impulse demand.',
            why_fail='Seasonal demand peak in autumn/winter; requires dedicated 120V outlet near water connection.',
            traffic_benchmark=TrafficBenchmark.P_25_50,
            confidence=TrafficConfidence.HIGH,
            exact_walmart_query='Camco heated water hose 25ft'
        ),
        walmart=WalmartResearchResult(
            search_query_used='Camco heated water hose 25ft',
            status=WalmartStatus.FOUND,
            displayed_price=74.99,
            url='https://www.walmart.com/search?q=Camco+heated+water+hose+25ft'
        )
    )

    # 3. RV Skylight Insulator Cover
    p3_raw = RawAmazonProduct(
        title='RV Skylight Insulator Cover 14x14 Inch with Reflective Thermal Layer, Magnetic Easy Fold Space Saving RV Vent Sun Shade',
        url='https://www.amazon.com/dp/B0D9M4T8QK',
        asin='B0D9M4T8QK',
        displayed_price=24.99,
        image_url='https://m.media-amazon.com/images/I/61r5T0vjUjL._AC_SL1500_.jpg',
        images=[
            'https://m.media-amazon.com/images/I/61r5T0vjUjL._AC_SL1500_.jpg',
            'https://m.media-amazon.com/images/I/71Y87t4vS7L._AC_SL1500_.jpg'
        ],
        bsr_rank='#8,950 in RV Vents & Skylights',
        category='RV Parts & Accessories',
        source_page_url='https://www.amazon.com/gp/new-releases/automotive/2258019011/'
    )
    p3_ver = VerifiedAmazonProduct(
        title=p3_raw.title,
        asin='B0D9M4T8QK',
        canonical_url='https://www.amazon.com/dp/B0D9M4T8QK',
        displayed_price=24.99,
        bsr=8950,
        bsr_rank=p3_raw.bsr_rank,
        images=p3_raw.images,
        bullet_points=[
            'Reflective thermal aluminum backing stops UV and radiant heat',
            'Foldable magnetic design for quick ventilation access',
            'Fits standard 14x14 inch RV roof vents and shower skylights'
        ],
        verification_state=VerificationState.VERIFIED
    )
    p3_scores = calculate_score_breakdown(
        raw=RawDimensionScores(
            facebook_discovery_potential=7.0,
            rv_facebook_exposure=6.0,
            rv_relevance=8.5,
            novelty_newness=6.0,
            problem_solving_power=7.0,
            visual_wow=6.0,
            space_convenience=7.5,
            impulse_click_potential=7.5,
            rv_audience_breadth=8.0,
        ),
        exposure_level=ExposureLevel.LOW,
        strong_didnt_know_existed=False
    )
    p3_cand = ProductCandidate(
        canonical_url='https://www.amazon.com/dp/B0D9M4T8QK',
        asin='B0D9M4T8QK',
        normalized_title=p3_raw.title.lower(),
        raw_product=p3_raw,
        verified_product=p3_ver,
        verification_state=VerificationState.VERIFIED,
        newness=NewnessStatus.NEW,
        exposure_level=ExposureLevel.LOW,
        scores=p3_scores,
        opportunity=ProductOpportunity(
            visual_hook='Infrared thermal camera showing 30F heat drop inside the RV cabin right under the skylight.',
            facebook_angle='Summer travel & desert camping tip: Drop your RV interior temp by 10-15 degrees instantly with zero power consumption.',
            why_next_winner='Reflective thermal barrier blocks heat transfer through 14x14 RV vents; low ticket, instant impulse buy with universal fit.',
            why_fail='High competition from generic bubble foil pads; slightly lower margin.',
            traffic_benchmark=TrafficBenchmark.P_25_50,
            confidence=TrafficConfidence.MEDIUM,
            exact_walmart_query='RV skylight insulator 14x14'
        ),
        walmart=WalmartResearchResult(
            search_query_used='RV skylight insulator 14x14',
            status=WalmartStatus.FOUND,
            displayed_price=26.50,
            url='https://www.walmart.com/search?q=RV+skylight+insulator+14x14'
        )
    )

    health = RunHealthReport(
        run_id='showcase_demo_benchmark',
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        categories_discovered=18,
        products_discovered=180,
        products_deduped=165,
        products_verified=150,
        products_evaluated=150,
        winners_found=2,
        near_misses_found=1,
        products_rejected=147,
        walmart_matches_found=3,
        google_sheets_updated=True,
        telegram_alert_sent=True,
        dashboard_generated=True,
        success=True
    )

    html_content = generate_executive_dashboard_html(
        reviewed_count=150,
        winners=[p1_cand, p2_cand],
        near_misses=[p3_cand],
        health=health,
        spreadsheet_id='13nQZOUdkOtSHsOI0X_f1FhuIa2q10RH2WTdIkF5C3Y0'
    )

    os.makedirs('data/reports', exist_ok=True)
    demo_path = os.path.join('data', 'reports', 'demo_showcase_dashboard.html')
    preview_path = os.path.join('data', 'reports', 'client_preview.html')

    with open(demo_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    with open(preview_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print('Showcase generated successfully!')
    print(f'Product 1 score: {p1_scores.total_score:.1f}, is_winner: {p1_scores.is_winner}')
    print(f'Product 2 score: {p2_scores.total_score:.1f}, is_winner: {p2_scores.is_winner}')
    print(f'Product 3 score: {p3_scores.total_score:.1f}, is_winner: {p3_scores.is_winner}')

if __name__ == '__main__':
    build_showcase()
