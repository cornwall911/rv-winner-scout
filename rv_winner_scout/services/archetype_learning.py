"""Archetype Learning Engine: Extracts and matches latent product DNA from Winners and Should-Be-Tested benchmarks."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class ArchetypeDefinition:
    """Represents a learned latent product archetype based on verified winners and strong candidates."""

    id: str
    badge_label: str
    archetype_class: str  # "WINNER" or "SHOULD_TEST"
    core_latent_value: str
    pain_points_relieved: List[str]
    key_mechanisms: List[str]
    exemplar_products: List[str]
    semantic_signals: List[str]
    subcategories: List[str]


# ---------------------------------------------------------------------------
# The Canonical Learned Archetypes Repository
# ---------------------------------------------------------------------------
LEARNED_ARCHETYPES: List[ArchetypeDefinition] = [
    ArchetypeDefinition(
        id="CLIMATE_INNOVATION",
        badge_label="❄️ Non-Invasive Climate Innovation",
        archetype_class="WINNER",
        core_latent_value="Complete temperature relief without invasive vehicle alterations or $2,000+ OEM replacement costs.",
        pain_points_relieved=["extreme campground heat", "freezing winter nights", "roof leaks from cutting holes", "excessive rooftop AC weight"],
        key_mechanisms=[
            "2-in-1 cooling & ceramic heating capability",
            "Zero structural cutting (no 14x14 roof cuts or window frame modifications)",
            "Ultra-compact wall mount or portable footprint (< 10 lbs)",
            "Plug-and-play operation for vans, teardrops, truck campers, and fifth wheels",
            "High perceived value vs expensive traditional rooftop AC replacements",
        ],
        exemplar_products=[
            "B0HDY4LYMX (Wall Mounted Ductless 2-in-1 AC/Heating)",
            "Arctic Air Evaporative Air Cooler (Walmart: https://walmrt.us/4eojgm9)",
            "Midea Window Air Conditioner (Walmart: https://walmrt.us/4qZdNYN)",
        ],
        semantic_signals=[
            "wall mounted air conditioner", "ductless air conditioner", "wall ac unit",
            "portable 2-in-1", "windowless air conditioner", "no window needed ac",
            "mini split portable", "ptc wall heating", "ductless rv cooling",
            "evaporative air cooler", "evaporative cooler", "window air conditioner",
            "portable air cooler", "personal air cooler",
        ],
        subcategories=[
            "RV Air Conditioners & Accessories",
            "Portable Heaters & Climate",
            "RV Ventilation & Air Flow",
        ],
    ),
    ArchetypeDefinition(
        id="OFFGRID_ENERGY_INDEPENDENCE",
        badge_label="⚡ Off-Grid Energy Freedom",
        archetype_class="SHOULD_TEST",
        core_latent_value="Overcomes electrical bottlenecks to unlock true off-grid boondocking and protect expensive RV electronics.",
        pain_points_relieved=["generator overload surge", "tripped campground pedestal breakers", "inability to run AC off-grid", "dead house batteries"],
        key_mechanisms=[
            "60-75% inrush compressor current reduction (soft starter)",
            "High-density LFP power storage for off-grid 120V loads",
            "Intelligent surge and low-voltage protection before dirty campground power enters coach",
            "Direct DIY inline installation without rewiring main coach breaker panel",
        ],
        exemplar_products=[
            "B0GYD3TVDV (RV AC Soft Starter Inrush Limiter)",
            "B0GY4TQ2P8 (Anker SOLIX S2000 Portable Power Station)",
        ],
        semantic_signals=[
            "soft start", "inrush limiter", "startup current reduction",
            "surge protector rv", "portable power station", "lfp battery rv",
            "inverter generator", "smart power management", "amp limiter",
        ],
        subcategories=[
            "RV Electrical & Solar",
            "Generators & Power Management",
            "Surge Protectors & Inverters",
        ],
    ),
    ArchetypeDefinition(
        id="ACTIVE_SANITATION_ODOR_ELIMINATION",
        badge_label="💨 Active Odor & Sanitation Elimination",
        archetype_class="SHOULD_TEST",
        core_latent_value="Active elimination of holding tank and black-water odors without chemical dependency.",
        pain_points_relieved=["foul black tank smell inside small camper", "cassette toilet chemical off-gassing", "clogged sewer pipes", "messy dump station spills"],
        key_mechanisms=[
            "Active negative pressure extraction venting odors through floor/exterior wall",
            "Macerator waste pulverization enabling long-distance uphill discharge",
            "Aero-venting caps leveraging vehicle wind to continuously draw fumes upward",
            "Zero chemical toxicity for boondockers and families",
        ],
        exemplar_products=[
            "B0HHY3BLNN (Exhaustrex RV Cassette Toilet Ventilation)",
            "B0GWCN2YMQ (Siphon RV Plumbing Vent Cap)",
        ],
        semantic_signals=[
            "cassette toilet ventilation", "toilet exhaust", "tank vent fan",
            "macerator pump", "siphon vent cap", "odor extraction",
            "black water odor", "holding tank vent", "sewer hose bayonet",
        ],
        subcategories=[
            "RV Sanitation & Sewer",
            "Plumbing & Holding Tanks",
            "Toilet Replacement Parts & Accessories",
        ],
    ),
    ArchetypeDefinition(
        id="CATASTROPHE_PREVENTION_SAFETY",
        badge_label="🛡️ Safety & Catastrophe Defense",
        archetype_class="SHOULD_TEST",
        core_latent_value="Early life-and-property catastrophe warnings that prevent catastrophic fires, gas poisoning, or high-pressure plumbing blowouts.",
        pain_points_relieved=["undetected propane leaks while sleeping", "ruptured PEX pipes from 100+ PSI campground water", "trailer tire blowout at 65 MPH"],
        key_mechanisms=[
            "12V hardwired constant gas/CO monitoring with loud audible alarms",
            "Integrated pressure regulation gauge preventing RV pipe rupture",
            "Direct replacement for 5-year expired factory OEM detectors",
            "Simple installation giving immense psychological peace of mind",
        ],
        exemplar_products=[
            "B0H6J7BP2P (12V RV Propane Gas Detector)",
            "B0H8HF9VH5 (Replacement RV LP Gas Alarm)",
        ],
        semantic_signals=[
            "propane gas detector", "lp detector rv", "gas leak detector",
            "water pressure regulator with gauge", "rv tpms", "tire pressure monitor rv",
            "co detector rv", "breakaway switch", "fire prevention rv",
        ],
        subcategories=[
            "RV Safety & Security",
            "Detectors & Alarms",
            "Water Pressure Regulators",
        ],
    ),
    ArchetypeDefinition(
        id="PASSIVE_THERMAL_BARRIER",
        badge_label="🌡️ Passive Thermal Barrier",
        archetype_class="SHOULD_TEST",
        core_latent_value="Zero-watt thermal regulation that drops interior camper temperatures by 15-20°F without drawing power.",
        pain_points_relieved=["massive greenhouse solar heat entering via skylight/vent", "winter heat loss through thin plastic vents", "rooftop rain noise"],
        key_mechanisms=[
            "Reflective multi-layer thermal aluminum film reflecting 97% of radiant UV heat",
            "High-density foam core blocking conduction and acoustic rain noise",
            "Friction-fit into standard 14x14 vent openings (zero tools or screws needed)",
            "Inexpensive cost with massive comfort dividend",
        ],
        exemplar_products=["B0GHF8P4CK (Cyrico RV Skylight Insulator 2-Pack)"],
        semantic_signals=[
            "skylight insulator", "vent pillow", "rv vent cover blackout",
            "insulated vent cushion", "reflective sunshade rv", "magnetic window insulator",
            "thermal vent shade",
        ],
        subcategories=[
            "RV Interior Accessories",
            "Vent Covers & Sunshades",
            "Insulation & Weatherproofing",
        ],
    ),
    ArchetypeDefinition(
        id="BOONDOCKING_WATER_PRESSURE_OPTIMIZATION",
        badge_label="🚿 Boondocking Water & Pressure Efficiency",
        archetype_class="SHOULD_TEST",
        core_latent_value="Drastically boosts weak RV shower pressure while halving fresh tank water consumption.",
        pain_points_relieved=["pathetic trickle RV shower pressure", "running out of fresh water in 2 days", "filling grey tank too fast"],
        key_mechanisms=[
            "High-velocity micro-nozzle pressure amplification",
            "Integrated one-touch pause / trickle shutoff switch for soaping up",
            "Reduces flow to 1.5 - 1.8 GPM without sacrificing shower sensation",
            "Direct screw-on replacement for standard RV shower arms",
        ],
        exemplar_products=["B0GZLLJ9PF (High Pressure RV Shower Head with Pause Switch)"],
        semantic_signals=[
            "rv shower head with hose", "high pressure shower head rv",
            "water saving pause switch", "rv shower replacement",
            "low flow high pressure rv", "fresh water saver",
        ],
        subcategories=[
            "RV Bath & Kitchen",
            "Shower Heads & Faucets",
            "Water Conservation & Pumps",
        ],
    ),
    ArchetypeDefinition(
        id="ELECTRONIC_VISIBILITY_ASSISTANCE",
        badge_label="👁️ Driving & Visibility Defense",
        archetype_class="RESEARCH_CANDIDATE",
        core_latent_value="Micro-cost exterior electronic protection that prevents glare and water droplets from blinding backup cameras.",
        pain_points_relieved=["blind backup camera in heavy rain", "backing a 35ft trailer in downpour", "sun glare washout"],
        key_mechanisms=[
            "Aerodynamic rain hood channeling water drops away from camera optics",
            "Carbon fiber / UV-resistant automotive adhesive install in 60 seconds",
            "Universal fit across Furrion, Haloview, and aftermarket RV cameras",
        ],
        exemplar_products=[
            "B0HHHV2RXX (Waterproof Rear View Camera Rain Shield)",
            "B0HDP7YCN4 (Carbon Fiber Backup Camera Rain Shield)",
        ],
        semantic_signals=[
            "rear view camera rain shield", "backup camera sun shade", "backup camera rain shield",
            "camera rain shield", "camera visor rv", "furrion camera hood", "waterproof camera cover",
        ],
        subcategories=[
            "RV Electronics & Cameras",
            "Backup Cameras & Monitors",
            "Exterior Hardware",
        ],
    ),
    ArchetypeDefinition(
        id="AIRFLOW_VENT_UPGRADE",
        badge_label="🌀 High-Flow Airflow & Vent Upgrade",
        archetype_class="SHOULD_TEST",
        core_latent_value="High-CFM quiet replacement motor upgrading noisy, weak factory RV roof fans into efficient climate exchangers.",
        pain_points_relieved=["noisy factory roof fan", "stuffy camper interior", "weak cooking exhaust"],
        key_mechanisms=[
            "Direct-drop upgrade kit converting standard vent into high-speed intake/exhaust",
            "Slashes cabin temperature within 10 minutes",
            "Fraction of cost of buying a whole new $300 Fantastic Fan assembly",
        ],
        exemplar_products=["B0GXSGH5BN (Upgrade Kit RV Roof Vent Fan Motor Replacement)"],
        semantic_signals=[
            "roof vent fan motor", "vent fan motor replacement", "rv vent fan upgrade",
            "fan motor replacement kit", "rv roof fan motor", "vent fan motor",
        ],
        subcategories=[
            "RV Ventilation & Air Flow",
            "Roof Vents & Fans",
        ],
    ),
    ArchetypeDefinition(
        id="ULTRASONIC_TANK_INTELLIGENCE",
        badge_label="📡 Non-Invasive Ultrasonic Tank Intelligence",
        archetype_class="WINNER",
        core_latent_value="Eliminates the #1 universal RV frustration: false sensor readings on black/grey tanks without drilling or nasty internal probes.",
        pain_points_relieved=["false tank sensor readings", "black tank overflowing unexpectedly", "drilling holes in waste tanks"],
        key_mechanisms=[
            "External acoustic/ultrasonic sensor sticking to tank underside",
            "Real-time Bluetooth percentage readout on smartphone",
            "Zero drilling, zero contact with black water sludge",
        ],
        exemplar_products=["Mopeka Pro Check Wireless Ultrasonic Tank Sensor"],
        semantic_signals=[
            "ultrasonic tank sensor", "tank level monitor rv", "black water sensor wireless",
            "holding tank sensor bluetooth", "magnetic tank sensor", "propane sensor bluetooth",
        ],
        subcategories=[
            "RV Sanitation & Sewer",
            "RV Electronics & Monitoring",
        ],
    ),
    ArchetypeDefinition(
        id="ENDLESS_ONDEMAND_HOT_WATER",
        badge_label="🔥 Endless On-Demand Hot Water",
        archetype_class="WINNER",
        core_latent_value="Eliminates the 6-gallon suburban water heater barrier, delivering unlimited hot showers and slashing water waste while boondocking.",
        pain_points_relieved=["running out of hot water in 2 minutes", "waiting 20 minutes between showers", "wasting boondocking fresh water waiting for warm water"],
        key_mechanisms=[
            "Instant flow-activated burner / recirculating heat exchanger",
            "Drop-in standard RV water heater door replacement",
            "Continuous hot water for multiple travelers without recovery lag",
        ],
        exemplar_products=["Fogatti / Furrion Tankless Instant RV Water Heater"],
        semantic_signals=[
            "tankless water heater rv", "instant water heater camper", "on demand water heater rv",
            "tankless rv water heater", "tankless gas water heater rv",
        ],
        subcategories=[
            "RV Plumbing & Water Heaters",
            "Water Systems & Pumps",
        ],
    ),
    ArchetypeDefinition(
        id="ZERODRILL_SOLAR_REVERSING",
        badge_label="👁️ Zero-Drill Wireless Reversing & Hitch Defense",
        archetype_class="WINNER",
        core_latent_value="Eliminates the anxiety, blind spots, and marital arguments of backing a 30ft trailer or hitching alone.",
        pain_points_relieved=["blind spot accidents when backing into campsite", "hitching trailer alone without a spotter", "fear of ripping trailer wires"],
        key_mechanisms=[
            "100% solar rechargeable magnetic base sticking directly to steel frame",
            "Zero wiring through trailer walls or splicing into tail lights",
            "Crisp digital anti-interference wireless display on dash",
        ],
        exemplar_products=["Haloview / Rohent Solar Wireless Backup Camera"],
        semantic_signals=[
            "solar wireless backup camera", "magnetic trailer camera", "rv backup camera solar",
            "wireless hitch camera magnetic", "trailer camera zero drill", "magnetic backup camera",
        ],
        subcategories=[
            "RV Electronics & Cameras",
            "Backup Cameras & Monitors",
        ],
    ),
    ArchetypeDefinition(
        id="QUICK_LEVEL_STABILIZATION",
        badge_label="⚖️ Quick-Level Cordless Stabilization",
        archetype_class="SHOULD_TEST",
        core_latent_value="Replaces the exhausting 20-minute struggle of hand-cranking jacks and stacking wooden blocks in campground mud.",
        pain_points_relieved=["hand cranking heavy jacks in dirt", "unlevel camper giving headaches or fridge failure", "trailer rocking in high wind"],
        key_mechanisms=[
            "Drill-socket adapter / rapid-drive stabilizer conversion",
            "Curved ramping levelers with non-slip chocks",
            "Digital smartphone bubble level leveling from driver seat",
        ],
        exemplar_products=["Beech Lane Curved RV Levelers / Scissor Jack Drill Adapter"],
        semantic_signals=[
            "curved leveler rv", "scissor jack drill adapter", "drill socket leveling jack",
            "wireless rv leveler", "rv leveler curved blocks", "camper leveler ramps",
        ],
        subcategories=[
            "Jacks & Leveling",
            "Hardware & Stabilizers",
        ],
    ),
    ArchetypeDefinition(
        id="PORTABLE_AIRFLOW_CIRCULATION",
        badge_label="🌀 Zero-Wire Portable Airflow & Circulation",
        archetype_class="WINNER",
        core_latent_value="Hanging USB/rechargeable ceiling fan or socket-screw air circulator for tight camper spaces without cutting holes or rewiring.",
        pain_points_relieved=["stifling camper air", "no ceiling fan wiring in bunk or tent", "noisy factory roof fans"],
        key_mechanisms=[
            "Rechargeable battery or standard light socket screw-in installation",
            "Multi-speed quiet breeze with remote control and integrated LED night light",
            "Zero wiring, zero drilling, zero tools needed",
        ],
        exemplar_products=[
            "bestmoument Portable Ceiling Fan (Walmart: https://walmrt.us/4xVwXBY)",
            "DAYBETTER Socket Fan Light (Walmart: https://walmrt.us/4qQyrKL)",
        ],
        semantic_signals=[
            "portable ceiling fan", "hanging ceiling fan", "usb ceiling fan",
            "socket fan light", "socket fan", "tent ceiling fan", "rechargeable ceiling fan",
        ],
        subcategories=[
            "RV Fans & Ventilation",
            "Lighting & Ceiling Fixtures",
            "Camping Tent Accessories",
        ],
    ),
    ArchetypeDefinition(
        id="OUTDOOR_CAMPSITE_LIVING",
        badge_label="🏕️ Outdoor Campsite Living & Kitchen",
        archetype_class="SHOULD_TEST",
        core_latent_value="Expands outdoor campsite living footprint and keeps smoke, grease, and clutter outside the small camper interior.",
        pain_points_relieved=["grease and smoke inside small camper kitchen", "lack of patio shade and privacy", "leaving expensive bikes exposed to rain"],
        key_mechanisms=[
            "Rapid set up flat-top griddle for full family outdoor meals",
            "Awning drop-screen blocking 85% UV solar heat and blowing dust",
            "Pop-up waterproof storage tent protecting e-bikes and gear",
        ],
        exemplar_products=[
            "Blackstone Outdoor Griddle (Walmart: https://walmrt.us/4dBTEmV)",
            "Dulepax RV Awning Screen (Walmart: https://walmrt.us/4qQyrKL)",
            "Bike Storage Tent (Walmart: https://walmrt.us/4yhHh6M)",
        ],
        semantic_signals=[
            "outdoor griddle", "tabletop griddle", "flat top grill",
            "awning screen", "rv awning shade", "sun shade screen",
            "bike storage tent", "bike tent", "outdoor storage tent",
        ],
        subcategories=[
            "RV Outdoor Kitchen & Grills",
            "Awnings & Screen Rooms",
            "Outdoor Gear Storage",
        ],
    ),
    ArchetypeDefinition(
        id="COMPACT_OFFGRID_APPLIANCES",
        badge_label="⚡ Compact RV Galley & Living Appliances",
        archetype_class="SHOULD_TEST",
        core_latent_value="Miniaturized high-efficiency appliances that bring luxury home comforts into camper galleys without blowing campground breakers.",
        pain_points_relieved=["running out of ice during dry camping", "costly laundromat stops on road trips", "pumping 5-gal water jugs manually"],
        key_mechanisms=[
            "Rapid bullet ice generation in under 6 minutes",
            "Twin-tub compact wash & spin dry without hookup dependence",
            "Rechargeable USB electric pump for fresh 5-gallon water jugs",
            "Compact low-wattage cooking via electric skillets and pop-up toasters",
        ],
        exemplar_products=[
            "Frigidaire Ice Maker (Walmart: https://walmrt.us/3RiaApe)",
            "ZENY Portable Washing Machine (Walmart: https://walmrt.us/3QlPZ3q)",
            "Electric Water Dispenser Pump (Walmart: https://walmrt.us/4xBMgPC)",
            "Brentwood Electric Skillet (Walmart: https://walmrt.us/4xPQcwB)",
            "Thyme Table Toaster (Walmart: https://walmrt.us/4yhHh6M)",
        ],
        semantic_signals=[
            "ice maker", "countertop ice maker", "portable washing machine",
            "mini washing machine", "water dispenser pump", "5 gallon water pump",
            "electric skillet", "table toaster", "portable skillet",
        ],
        subcategories=[
            "RV Kitchen & Galley",
            "Compact Appliances",
            "Laundry & Housewares",
        ],
    ),
    ArchetypeDefinition(
        id="SPACE_SAVING_CONVERTIBLE_FURNITURE",
        badge_label="🛋️ Space-Saving Convertible Furniture",
        archetype_class="SHOULD_TEST",
        core_latent_value="Dual-purpose folding furniture that converts cramped camper living spaces into comfortable full-size beds in seconds.",
        pain_points_relieved=["lack of guest sleeping space", "bulky uncomfortable camper dinettes", "awkward floorplans in small travel trailers"],
        key_mechanisms=[
            "Multi-angle folding backrest converting couch into flat sleeper bed",
            "Lightweight frame tailored for RV door widths and floor loading limits",
            "High-density foam seating with washable easy-clean upholstery",
        ],
        exemplar_products=[
            "Aiho Sleeper Sofa Bed (Walmart: https://walmrt.us/4qZdNYN)",
            "Gewnee Sleeper Sofa (Walmart: https://walmrt.us/4bsZJiQ)",
        ],
        semantic_signals=[
            "sleeper sofa", "sofa bed", "futon sofa bed",
            "convertible sofa", "folding sofa bed", "rv couch bed",
        ],
        subcategories=[
            "RV Furniture",
            "Living Room & Sofas",
            "Beds & Mattresses",
        ],
    ),
    ArchetypeDefinition(
        id="SAFETY_TRANSIT_ORGANIZATION",
        badge_label="🔒 Safe Transit & Space Organization",
        archetype_class="SHOULD_TEST",
        core_latent_value="Zero-fall transit organization and window sun defense keeping items locked down during rough highway towing.",
        pain_points_relieved=["sharp knives flying off counters on bumpy roads", "rattling messy galley drawers", "harsh glare and heat through entry door window"],
        key_mechanisms=[
            "Heavy-duty neodymium magnetic wall bar securing culinary knives",
            "Expanding bamboo dividers organizing silverware and tools",
            "Thin shade blackout kit replacing cheap factory entry door frosted glass",
        ],
        exemplar_products=[
            "Magnetic Knife Holder (Walmart: https://walmrt.us/41mMwU8)",
            "Royal Craft Wood Drawer Organizer (Walmart: https://walmrt.us/4vYKBmw)",
            "AP Products Thin Shade Kit (Walmart: https://walmrt.us/4wiZHTS)",
        ],
        semantic_signals=[
            "magnetic knife holder", "magnetic knife bar", "knife strip",
            "drawer organizer", "bamboo drawer divider", "silverware organizer",
            "thin shade kit", "entry door shade", "rv door window shade",
        ],
        subcategories=[
            "RV Organization & Storage",
            "Interior Safety Hardware",
            "Window Shades & Blinds",
        ],
    ),
]



class ArchetypeMatcher:
    """Matches raw and verified product data against learned winning and testing archetypes."""

    @classmethod
    def match_candidate(cls, title: str, bullet_points: Optional[List[str]] = None) -> Optional[ArchetypeDefinition]:
        """Identifies the best matching learned archetype based on semantic signals and functional traits."""
        text = f"{title} {' '.join(bullet_points or [])}".lower()

        # Prioritize WINNER class archetypes first
        for arch in LEARNED_ARCHETYPES:
            if arch.archetype_class == "WINNER":
                for signal in arch.semantic_signals:
                    if signal in text:
                        return arch

        # Then SHOULD_TEST class archetypes
        for arch in LEARNED_ARCHETYPES:
            if arch.archetype_class == "SHOULD_TEST":
                for signal in arch.semantic_signals:
                    if signal in text:
                        return arch

        # Finally, any remaining archetypes
        for arch in LEARNED_ARCHETYPES:
            for signal in arch.semantic_signals:
                if signal in text:
                    return arch

        return None

    @classmethod
    def get_ai_learning_prompt_appendix(cls) -> str:
        """Generates a structured prompt block detailing the learned latent archetypes for LLM evaluation."""
        lines = [
            "### LEARNED WINNING & TESTING ARCHETYPES (Benchmark DNA):",
            "Do NOT evaluate merely based on brand name or exterior shape. Evaluate whether the product embodies one of these proven high-converting latent value archetypes:",
            "",
        ]
        for arch in LEARNED_ARCHETYPES:
            lines.append(f"**[{arch.badge_label}]** ({arch.archetype_class})")
            lines.append(f"- Core Value: {arch.core_latent_value}")
            lines.append(f"- Key Functional Mechanisms: {'; '.join(arch.key_mechanisms[:3])}")
            lines.append(f"- Proven Exemplars: {', '.join(arch.exemplar_products)}")
            lines.append("")

        lines.append(
            "When a product embodies any of these functional value drivers with low cost/easy DIY install, score its problem_solving_power, facebook_discovery_potential, and impulse_click_potential enthusiastically!"
        )
        return "\n".join(lines)
