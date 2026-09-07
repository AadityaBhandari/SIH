# ==============================================================================
# ARIA - Astronaut Research Interaction Assistant
# Embedded Scientific Datasets: 7 Microgravity Experiments, Timeline & Emergencies
# ==============================================================================

EMBEDDED_EXPERIMENTS = [
  {
    "id": "EXP-01",
    "code": "VOY-TARDIGRADE",
    "title": "Voyager Tardigrade: Microgravity Survival & Transcriptome Study",
    "category": "Astrobiology & Extremophile Genetics",
    "principal_investigator": "Dr. E. Vance / ISRO-NASA Astrobiology Working Group",
    "objective": "Investigate cryptobiosis revival dynamics, DNA repair fidelity, and differential transcriptome expression of eutardigrades (Hypsibius exemplaris & Milnesium tardigradum) exposed to cosmic ionizing radiation and microgravity.",
    "facility": "Life Sciences Glovebox (LSG) & MELFI -80\u00b0C Cryo-Freezer",
    "duration_hours": 72,
    "critical_window_minutes": 30,
    "safety_level": "Tier 2 - Bio-Cryo Precaution",
    "environmental_requirements": {
      "temperature_celsius": "21.5 \u00b1 0.5",
      "co2_pct": "< 0.40",
      "relative_humidity_pct": "45 - 55",
      "radiation_limit_micro_sv_h": "35.0"
    },
    "hazards": [
      "Cryogenic thermal burn from -80\u00b0C MELFI freezer transfers",
      "RNAlater fixative skin/eye irritant -- avoid aerosolization in cabin",
      "Micro-droplet dispersion during hydration in zero-G"
    ],
    "steps": [
      {"step_number": 1, "title": "LSG Airlock Verification & Glove Integrity Check", "action": "Inspect Life Sciences Glovebox negative pressure barrier (-0.5 in. w.g.) and execute gauntlet pinhole inspection before transferring Tardigrade Cassette #01.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Do not open outer airlock if LSG delta pressure is above -0.2 in. w.g."},
      {"step_number": 2, "title": "Cassette Desiccation Depressurization Equalization", "action": "Connect slow-bleed valve V-12 to the Tardigrade Desiccation Chamber to equalize chamber pressure with cabin atmosphere at a rate not exceeding 5 kPa/min.", "time_estimate_mins": 8, "is_mandatory": True, "requires_confirmation": True, "warning": "Rapid pressure equalization will cause mechanical shearing of tun-state tardigrade cuticles."},
      {"step_number": 3, "title": "Controlled Rehydration Injection", "action": "Inject 150 uL of sterile Spring Water Buffer via micro-perfusion port A-1 into well arrays using the zero-G capillary pipette. Verify meniscus lock.", "time_estimate_mins": 12, "is_mandatory": True, "requires_confirmation": True, "warning": "Ensure no microgravity air bubble entrapment over the cryptobiotic specimens."},
      {"step_number": 4, "title": "Revival Monitoring & Motility Index Logging", "action": "Engage LSG High-Resolution Macro-Imager at 40x magnification. Count active appendages and calculate motile revival percentage at T+4 hours.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": False, "warning": "Record motility score in accordance with Astrobiology Protocol Metric TAP-4."},
      {"step_number": 5, "title": "Transcriptome Fixation via RNAlater Injection", "action": "Inject 300 uL of chilled RNAlater fixative into Well Set B to halt transcription and stabilize mRNA. Complete injection within the critical 30-minute window.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "CRITICAL PROTOCOL: Delays past 30 minutes cause heat-shock mRNA degradation, corrupting transcriptome data."},
      {"step_number": 6, "title": "Cryogenic Preservation & MELFI Stowage", "action": "Seal Fixation Cassette in double zip-containment bag and transfer to MELFI Dewar #2 (-80C cavity) within 15 minutes of fixation.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Don cryogenic safety gauntlets and face shield. Check MELFI seal indicator."}
    ]
  },
  {
    "id": "EXP-02",
    "code": "MYO-LSG-GEN",
    "title": "Myogenesis Study: Muscle Atrophy & Stem Cell Regeneration",
    "category": "Human Space Physiology & Cell Biology",
    "principal_investigator": "Prof. A. Nair / Space Medicine & Biomolecular Directorate",
    "objective": "Investigate satellite stem cell proliferation, Pax7/MyoD transcriptional dynamics, and electrical pulse stimulation (EPS) induced regeneration in microgravity using the Life Sciences Glovebox.",
    "facility": "Life Sciences Glovebox (LSG) & Confocal Fluorescence Imager",
    "duration_hours": 96,
    "critical_window_minutes": 20,
    "safety_level": "Tier 3 - Human Biological Specimen & High Voltage",
    "environmental_requirements": {
      "temperature_celsius": "37.0 \u00b1 0.2",
      "co2_pct": "5.0 \u00b1 0.1",
      "relative_humidity_pct": "95.0 \u00b1 2.0",
      "radiation_limit_micro_sv_h": "30.0"
    },
    "hazards": [
      "Biohazard Level 2 containment breach in cabin",
      "Paraformaldehyde (PFA 4%) toxic respiratory and ocular irritant",
      "Electrical short circuit during 1Hz EPS pulse excitation in LSG"
    ],
    "steps": [
      {"step_number": 1, "title": "LSG Bio-Safety Barrier & Gauntlet Seal Check", "action": "Run LSG automated hermetic leak test. Verify HEPA filtration airflow (150 CFM) and gauntlet pressure differential before donning.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "MANDATORY SAFETY: Operating with a compromised glove will trigger biohazard cabin quarantine."},
      {"step_number": 2, "title": "Incubation Chamber Temperature & Gas Baseline", "action": "Verify Myogenesis Incubator module telemetry: Chamber T = 37.0C, CO2 = 5.0%, O2 = 20.9%. Log baseline stability for 15 minutes.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Do not proceed if temperature fluctuates by more than +/-0.3C."},
      {"step_number": 3, "title": "Perfusion Media Exchange (DMEM Differentiation Medium)", "action": "Using sterile peristaltic syringe driver, aspirate exhausted growth medium and slowly perfuse 12 mL of 37C pre-warmed DMEM containing 2% Horse Serum.", "time_estimate_mins": 20, "is_mandatory": True, "requires_confirmation": True, "warning": "Avoid shear stress on delicate myotube monolayers during fluid injection."},
      {"step_number": 4, "title": "Electrical Pulse Stimulation (EPS) Rig Setup", "action": "Attach platinum electrode leads to Bio-Chip Array Alpha. Initiate 1 Hz, 2 ms bipolar pulses at 15 V for a continuous 60-minute stimulation cycle.", "time_estimate_mins": 60, "is_mandatory": True, "requires_confirmation": True, "warning": "Monitor impedance gauge. Disconnect immediately if electrode resistance exceeds 2.5 kOhm."},
      {"step_number": 5, "title": "Cellular Fixation with 4% Paraformaldehyde (PFA)", "action": "Within 20 minutes post-stimulation, infuse 4% PFA fixative through microfluidic chamber to freeze actin-myosin crossbridges and preserve Pax7 markers.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "CRITICAL HAZARD: Handle PFA strictly within negative pressure airflow. Double-seal waste cassette."},
      {"step_number": 6, "title": "Immunofluorescence Staining & Microscopy Scan", "action": "Stain with anti-MyoD fluorophore and DAPI counter-stain. Capture 3D confocal z-stack tiles across 10 regions of interest.", "time_estimate_mins": 30, "is_mandatory": True, "requires_confirmation": False, "warning": "Dim cabin lights in glovebox zone to prevent fluorophore photobleaching."}
    ]
  },
  {
    "id": "EXP-03",
    "code": "GERM-METHI-MOONG",
    "title": "Sprouting of Methi & Moong Seeds: Seed Germination in Microgravity",
    "category": "Space Agriculture & Plant Biology",
    "principal_investigator": "Dr. R. Sharma / ICAR-ISRO Plant Space Biology Team",
    "objective": "Analyze germination efficiency, root gravitropism disruption, capillary moisture management, and nutritional antioxidant synthesis in Vigna radiata (moong) and Trigonella foenum-graecum (methi).",
    "facility": "Advanced Plant Habitat (APH) Growth Chamber",
    "duration_hours": 120,
    "critical_window_minutes": 45,
    "safety_level": "Tier 1 - Botanical Containment",
    "environmental_requirements": {
      "temperature_celsius": "23.0 \u00b1 1.0",
      "co2_pct": "0.12 \u00b1 0.02 (1200 ppm)",
      "relative_humidity_pct": "70 - 80",
      "radiation_limit_micro_sv_h": "25.0"
    },
    "hazards": [
      "Uncontrolled water droplet breakaway in cabin electronics",
      "Microbial or fungal mold spore propagation in damp seed beds",
      "High relative humidity condensation on optical glass"
    ],
    "steps": [
      {"step_number": 1, "title": "APH Growth Cassette Installation & Wick Inspection", "action": "Seat Moong-Methi Dual Growth Cassette #3 into APH Bay 2. Check hydrophilic porous wick alignment and water supply manifold couplings.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Verify mechanical latch click. An unlatched cassette will cause fluid line decoupling."},
      {"step_number": 2, "title": "Capillary Hydro-Gel Hydration Priming", "action": "Prime capillary wicks with 25.0 mL of oxygenated Hoagland nutrient solution. Monitor moisture sensor telemetry until soil moisture reaches 65%.", "time_estimate_mins": 20, "is_mandatory": True, "requires_confirmation": True, "warning": "Excess moisture (>85%) will drown embryo radicles due to lack of gravity drainage."},
      {"step_number": 3, "title": "Zero-G Dark Incubation Initiation (48h Phase)", "action": "Seal light baffle doors and set APH photoperiod to 0 hours light / 24 hours dark for the initial 48-hour germination surge.", "time_estimate_mins": 5, "is_mandatory": True, "requires_confirmation": True, "warning": "Do not open chamber door during dark incubation to prevent premature photomorphogenesis."},
      {"step_number": 4, "title": "Radicle Emergence & Germination Index Tally", "action": "Engage autonomous multispectral top-down camera. Verify germination count: confirm at least 80% radicle protrusion in moong and 75% in methi.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": False, "warning": "Log fungal discoloration immediately if white hyphae are detected."},
      {"step_number": 5, "title": "Photoperiod Transition (16h Light / 8h Dark)", "action": "Initiate LED grow spectrum (Red 660nm : Blue 450nm : Far-Red 730nm at 120 umol/m2/s) to induce chlorophyll synthesis and antioxidant accumulation.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Verify cooling airflow duct is clear to prevent thermal leaf tip scorch."},
      {"step_number": 6, "title": "Harvest & Lyophilization Sampling", "action": "Harvest 10 sprouted seedlings of each species using sterile shears. Place into foil cryo-vials and transfer to Lyophilizer Unit for vitamin C preservation.", "time_estimate_mins": 25, "is_mandatory": True, "requires_confirmation": True, "warning": "Handle sprouts gently to preserve fragile microgravity hypocotyl cellular structures."}
    ]
  },
  {
    "id": "EXP-04",
    "code": "CYANO-ECLSS-GROWTH",
    "title": "Cyanobacteria Growth in Microgravity: Urea vs Nitrate Proteomics",
    "category": "Bioregenerative ECLSS & Proteomics",
    "principal_investigator": "Dr. K. Sundaram / Environmental Control & Life Support Lab",
    "objective": "Analyze photosynthetic productivity, biomass doubling time, and proteomics differential of Synechococcus elongatus cultured with human urine-derived urea versus potassium nitrate.",
    "facility": "Vega Photobioreactor Loop & Centrifuge Separator",
    "duration_hours": 144,
    "critical_window_minutes": 30,
    "safety_level": "Tier 2 - Bioreactor Fluidics & Pressure",
    "environmental_requirements": {
      "temperature_celsius": "30.0 \u00b1 0.5",
      "co2_pct": "1.50 \u00b1 0.10",
      "relative_humidity_pct": "50 - 60",
      "radiation_limit_micro_sv_h": "30.0"
    },
    "hazards": [
      "Bioreactor loop overpressurization (> 150 kPa)",
      "Ammonia/urea vapor breakdown odor and respiratory irritation",
      "Centrifuge imbalance in microgravity spinning at 4,000 RPM"
    ],
    "steps": [
      {"step_number": 1, "title": "Photobioreactor Fluidic Loop Sterility & Pressure Test", "action": "Pressurize closed PBR circuit to 120 kPa with sterile nitrogen. Run automated 5-minute decay test to rule out fluid line micro-leaks.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Do not introduce cyanobacterial inoculant if loop pressure drops > 1 kPa/min."},
      {"step_number": 2, "title": "Dual-Chamber Inoculation (Chamber A: Urea / Chamber B: Nitrate)", "action": "Inject 50 mL Synechococcus starter culture into Chamber A (Urea 15 mM) and Chamber B (KNO3 15 mM). Verify active peristaltic mixing (10 mL/min).", "time_estimate_mins": 20, "is_mandatory": True, "requires_confirmation": True, "warning": "Verify one-way check valves are seated to prevent cross-contamination between chambers."},
      {"step_number": 3, "title": "Gas Exchange Membrane & CO2 Sparging Calibration", "action": "Set CO2 enrichment supply to 1.5% at a sparging rate of 5 mL/min. Calibrate inline optical dissolved oxygen (DO) sensors.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Confirm that microgravity bubble separator membrane is free of biofilm clogging."},
      {"step_number": 4, "title": "Spectrophotometric Optical Density (OD720) Daily Logging", "action": "Extract 1.0 mL aliquot via septum port into zero-G optical cuvette. Measure absorbance at 720 nm and record photosynthetic quantum yield (Fv/Fm).", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": False, "warning": "Clean cuvette exterior with optical microfiber to eliminate condensation artifacts."},
      {"step_number": 5, "title": "Biomass Pellet Centrifugation & Protein Flash Freezing", "action": "Transfer 30 mL dense culture into microgravity-rated swinging bucket centrifuge. Spin at 3,500 RPM for 10 mins. Decant supernatant and flash freeze pellet.", "time_estimate_mins": 25, "is_mandatory": True, "requires_confirmation": True, "warning": "CRITICAL: Strictly counterbalance centrifuge tubes to within +/-0.05 grams to prevent zero-G vibration damage."}
    ]
  },
  {
    "id": "EXP-05",
    "code": "ALGAE-SPACE-CULT",
    "title": "Space Microalgae Cultivation: Edible Biomass & Air Revitalization",
    "category": "Space Nutrition & Life Support Systems",
    "principal_investigator": "Dr. H. Chen / European-Asian Microalgae Space Consortium",
    "objective": "Evaluate growth kinetics, lipid accumulation, and CO2 scrubbing efficiency of edible Chlorella vulgaris in a microgravity continuous-harvest bioreactor.",
    "facility": "EMCS (European Modular Cultivation System) Photobioreactor",
    "duration_hours": 168,
    "critical_window_minutes": 40,
    "safety_level": "Tier 1 - Food Grade Bioculture",
    "environmental_requirements": {
      "temperature_celsius": "25.0 \u00b1 0.5",
      "co2_pct": "2.00 \u00b1 0.15",
      "relative_humidity_pct": "40 - 50",
      "radiation_limit_micro_sv_h": "25.0"
    },
    "hazards": [
      "Algal biofilm fouling on LED light guides",
      "Air revitalization duct pressure drop",
      "Aerosolized microalgae dust inhalation during dry mass processing"
    ],
    "steps": [
      {"step_number": 1, "title": "Photobioreactor Membrane Cartridge Docking", "action": "Slide Chlorella Cultivation Cartridge #04 into EMCS rotor bay. Engage quick-disconnect fluid fittings and verify liquid lock indicators.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Ensure latch pins engage fully to prevent fluid escape under centrifugal motion."},
      {"step_number": 2, "title": "BG-11 Nutrient Medium Injection & Circulation", "action": "Prime system with 250 mL sterile modified BG-11 medium. Initiate internal peristaltic rotor pump at 15 RPM for homogeneous nutrient diffusion.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Inspect transparent manifold tubing for cavitation or gaseous froth bubbles."},
      {"step_number": 3, "title": "Continuous CO2 Absorption & O2 Evolution Telemetry", "action": "Link bioreactor exhaust line to cabin atmosphere scrubbing sensor. Verify net CO2 uptake exceeds 0.85 g CO2/L/day and log oxygen evolution rate.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": False, "warning": "If dissolved oxygen exceeds 250% saturation, activate bubble purge cycle."},
      {"step_number": 4, "title": "Optical Density OD680 & Chlorophyll Fluorometry", "action": "Record daily optical density at 680 nm. Perform Pulse-Amplitude-Modulation (PAM) fluorometry to calculate photosystem II operating efficiency.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Recalibrate zero-absorbance baseline using sterile BG-11 blank tube."},
      {"step_number": 5, "title": "Microfiltration Harvest & Nutritional Assay Sampling", "action": "Pass 100 mL of dense culture through 0.45 um hydrophilic membrane filter. Scrape green algae biomass cake into lyophilizer tube for protein/lipid assay.", "time_estimate_mins": 25, "is_mandatory": True, "requires_confirmation": True, "warning": "Wear surgical mask and eye protection during biomass cake scraping in zero-G."}
    ]
  },
  {
    "id": "EXP-06",
    "code": "CROP-SEED-EXPO",
    "title": "Food Crop Seeds Exposure Study: Cosmic Radiation & Mutagenesis",
    "category": "Agricultural Space Genetics & Radiation Biology",
    "principal_investigator": "Dr. M. Swaminathan / National Seed Space Exposure Project",
    "objective": "Quantify chromosomal aberrations, membrane lipid peroxidation, and post-flight germination vigor in dry seeds of regional rice, horse gram, sesame, eggplant, and tomato exposed to outer space cosmic radiation.",
    "facility": "JEM-EF / External Science Platform Airlock & Radiation Dosimeter Bay",
    "duration_hours": 336,
    "critical_window_minutes": 60,
    "safety_level": "Tier 2 - Airlock Vacuum & Thermal Extremes",
    "environmental_requirements": {
      "temperature_celsius": "Passive (-60C to +80C exterior / 21C interior)",
      "co2_pct": "Ambient cabin",
      "relative_humidity_pct": "< 20 (hermetic dry desiccant)",
      "radiation_limit_micro_sv_h": "Exterior cosmic ray flux"
    },
    "hazards": [
      "Thermal skin burn when retrieving vacuum-exposed cassette (-60C to +80C)",
      "Airlock depressurization and hatch seal contamination",
      "Desiccant dust release in cabin atmosphere"
    ],
    "steps": [
      {"step_number": 1, "title": "Hermetic Seed Cassette Seal & Barcode Verification", "action": "Verify tamper-proof O-ring hermetic seal and scan individual RFIDs for all 5 crop seed compartments: Rice, Horse Gram, Sesame, Eggplant, and Tomato.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": True, "warning": "Check desiccant silica indicator color (must be vivid blue, not pink)."},
      {"step_number": 2, "title": "Thermoluminescent Dosimeter (TLD) Insertion", "action": "Mount passive TLD dosimeters and CR-39 nuclear track detector plates directly adjacent to seed layers to capture high-LET heavy ion trajectories.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Handle dosimeters using anti-static tweezers to prevent electrostatic discharge."},
      {"step_number": 3, "title": "Airlock Slide Table Mounting & Depressurization", "action": "Fasten Seed Exposure Tray onto the JEM slide table. Secure robotic interface bolt. Evacuate airlock chamber to space vacuum (< 10^-3 Pa).", "time_estimate_mins": 45, "is_mandatory": True, "requires_confirmation": True, "warning": "MANDATORY SAFETY: Clear all personnel from airlock vicinity before vacuum valve opening."},
      {"step_number": 4, "title": "External Platform Deployment & Solar/Cosmic Exposure", "action": "Extend robotic arm to position tray on External Facility facing ram-orbit direction for 14-day cumulative high-energy proton/neutron bombardment.", "time_estimate_mins": 30, "is_mandatory": True, "requires_confirmation": True, "warning": "Monitor thermal sensor telemetry. Notify ground control if cassette exceeds +85C."},
      {"step_number": 5, "title": "Cassette Retrieval, Repressurization & Containment Stowage", "action": "Retract tray into airlock, repressurize chamber with cabin air at 10 kPa/min, don thermal insulated gloves, and stow cassette into hermetic return locker.", "time_estimate_mins": 35, "is_mandatory": True, "requires_confirmation": True, "warning": "Thermal shock hazard: Allow cassette to reach thermal equilibrium (+20C) before unclamping."}
    ]
  },
  {
    "id": "EXP-07",
    "code": "VOY-DISP-ISO9241",
    "title": "Voyager Displays: Human Interaction with Electronic Displays (ISO 9241)",
    "category": "Astronaut Ergonomics, Spatial Cognition & ISO 9241",
    "principal_investigator": "Dr. S. Kulkarni / Space Human Factors & Neuroergonomics Group",
    "objective": "Evaluate cognitive workload, target acquisition latency (Fitts' Law), visual saccadic degradation, and vestibular disorientation during astronaut interaction with space station electronic displays under ISO 9241-11 usability standards.",
    "facility": "Crew Quarters & Cockpit Electronic Flight Bags (EFB)",
    "duration_hours": 48,
    "critical_window_minutes": 15,
    "safety_level": "Tier 1 - Neurocognitive Fatigue & Vestibular Risk",
    "environmental_requirements": {
      "temperature_celsius": "22.0 \u00b1 1.0",
      "co2_pct": "< 0.35 (elevated CO2 degrades cognition)",
      "relative_humidity_pct": "40 - 50",
      "radiation_limit_micro_sv_h": "25.0"
    },
    "hazards": [
      "Vestibular space motion sickness (SMS) triggered by rapid 3D mental rotation tasks",
      "Severe ocular dry-eye and eye fatigue under zero-G fluid shift conditions",
      "Cognitive overload during mission-critical telemetry monitoring"
    ],
    "steps": [
      {"step_number": 1, "title": "Near-Infrared Saccadic Eye-Tracker Calibration", "action": "Don eye-tracking sensor headset. Perform 9-point visual calibration on primary cockpit display. Verify gaze tracking accuracy < 0.5 degrees.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Ensure display ambient glare is minimized and pupil diameter baseline is locked."},
      {"step_number": 2, "title": "Physiological Baseline Sync (HRV, Galvanic Skin & EEG)", "action": "Connect telemetry chest patch and biosensor headband. Synchronize heart rate variability (HRV) and skin conductance telemetry stream with test session clock.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Confirm electrode impedance is below 10 kOhm before starting cognitive test run."},
      {"step_number": 3, "title": "3D Shepard-Metzler Mental Rotation & Spatial Disorientation Battery", "action": "Complete 30 trials of 3D polygonal mental rotation against microgravity pitch/roll illusions. Record reaction time and error rate.", "time_estimate_mins": 20, "is_mandatory": True, "requires_confirmation": False, "warning": "If nausea or dizziness score exceeds 3 on Coriolis Scale, pause test immediately."},
      {"step_number": 4, "title": "Fitts' Law Touch Target Acquisition Latency Test", "action": "Perform ISO 9241-9 multi-directional touch pointing tasks on high-contrast glove-friendly interface at target widths of 24px, 48px, and 72px.", "time_estimate_mins": 15, "is_mandatory": True, "requires_confirmation": False, "warning": "Wear simulated EVA/IVA suit glove to benchmark touch input degradation."},
      {"step_number": 5, "title": "NASA-TLX Subjective Workload Assessment & ISO 9241 Scoring", "action": "Complete NASA-Task Load Index ratings across 6 dimensions: Mental Demand, Physical Demand, Temporal Demand, Performance, Effort, and Frustration.", "time_estimate_mins": 10, "is_mandatory": True, "requires_confirmation": True, "warning": "Submit subjective assessment within 10 minutes of test completion for valid memory recall."}
    ]
  }
]

EMBEDDED_TIMELINE = {
  "mission_name": "SIH-ORBITAL-STATION-ALPHA",
  "flight_increment": "INC-71",
  "commander": "Astronaut A. Rathore",
  "flight_surgeon": "Dr. K. Williams (Ground)",
  "active_flight_day": "FD-04",
  "schedule": [
    {
      "flight_day": "FD-01",
      "phase": "Post-Docking & Habitat Stabilization",
      "tasks": [
        {"time": "08:00", "experiment_id": "EXP-01", "task": "Stowage transfer of Tardigrade Cassette to LSG Holding", "status": "COMPLETED"},
        {"time": "14:00", "experiment_id": "EXP-06", "task": "Seed Cassette verification & dosimeter installation", "status": "COMPLETED"}
      ]
    },
    {
      "flight_day": "FD-02",
      "phase": "Microbiology & Plant Initiation",
      "tasks": [
        {"time": "09:30", "experiment_id": "EXP-03", "task": "Moong-Methi Seed Cassette installation in APH", "status": "COMPLETED"},
        {"time": "13:00", "experiment_id": "EXP-04", "task": "PBR circuit leak test & nitrogen pressure check", "status": "COMPLETED"}
      ]
    },
    {
      "flight_day": "FD-03",
      "phase": "Extremophile Revival & Algae Inoculation",
      "tasks": [
        {"time": "10:15", "experiment_id": "EXP-01", "task": "Tardigrade slow depressurization & rehydration", "status": "COMPLETED"},
        {"time": "15:45", "experiment_id": "EXP-05", "task": "Chlorella PBR cartridge docking & BG-11 injection", "status": "COMPLETED"}
      ]
    },
    {
      "flight_day": "FD-04",
      "phase": "Active Protocol Execution Day (CURRENT)",
      "tasks": [
        {"time": "09:00", "experiment_id": "EXP-02", "task": "Myogenesis Study: LSG Glove check & Perfusion media exchange", "status": "IN_PROGRESS"},
        {"time": "11:30", "experiment_id": "EXP-01", "task": "Tardigrade T+24h motility audit & RNAlater Fixation injection", "status": "PENDING"},
        {"time": "14:00", "experiment_id": "EXP-03", "task": "Moong-Methi germination emergence camera tally", "status": "PENDING"},
        {"time": "16:30", "experiment_id": "EXP-07", "task": "Voyager Displays: Eye-tracker calibration & 3D mental rotation test", "status": "PENDING"}
      ]
    },
    {
      "flight_day": "FD-05",
      "phase": "Mid-Mission Proteomics & Harvest",
      "tasks": [
        {"time": "09:00", "experiment_id": "EXP-04", "task": "Cyanobacteria OD720 logging & PBR biomass pellet centrifugation", "status": "PLANNED"},
        {"time": "13:30", "experiment_id": "EXP-05", "task": "Chlorella microfiltration harvest & lipid assay preparation", "status": "PLANNED"}
      ]
    },
    {
      "flight_day": "FD-06",
      "phase": "Airlock Retrieval & Ergonomics Re-test",
      "tasks": [
        {"time": "10:00", "experiment_id": "EXP-06", "task": "Airlock retrieval of cosmic radiation seed exposure tray", "status": "PLANNED"},
        {"time": "15:00", "experiment_id": "EXP-07", "task": "Voyager Displays: Fitts' Law touch test & NASA-TLX submission", "status": "PLANNED"}
      ]
    }
  ]
}

EMBEDDED_EMERGENCIES = [
  {
    "id": "EMERG-01",
    "code": "LSG-GLOVE-RUPTURE",
    "title": "Life Sciences Glovebox Glove Barrier Puncture / Biohazard Breach",
    "severity": "CRITICAL",
    "audio_alarm": "ALARM_BIOHAZARD_KLAXON",
    "immediate_actions": [
      "IMMEDIATELY withdraw hands into LSG gauntlet cuff safety clamps.",
      "Engage LSG Emergency High-Vacuum Scavenge Mode (Toggle switch SW-4).",
      "Verify negative pressure differential jumps to > -1.2 in. w.g. to contain airborne pathogens.",
      "Don emergency respiratory mask (Quick-Don 40) located at bulkhead 3.",
      "Seal outer LSG gauntlet cover ports and verify red containment LED locks.",
      "Alert Station Commander and transmit telemetry flag BIO-01 to Ground Flight Surgeon."
    ],
    "recovery_steps": [
      "Perform optical gauntlet dye leak inspection.",
      "Decontaminate exterior glove interface with 70% isopropyl alcohol wipe packet.",
      "Do not unseal LSG main front door until air filtration loop cycles 6 chamber volume changes (18 minutes)."
    ]
  },
  {
    "id": "EMERG-02",
    "code": "CHEM-PFA-SPILL",
    "title": "Toxic Paraformaldehyde (PFA 4%) Chemical Spill in Microgravity",
    "severity": "HIGH",
    "audio_alarm": "ALARM_TOXIC_SPILL",
    "immediate_actions": [
      "Cease experiment immediately. Do not attempt to wipe liquid with dry wipes (prevents droplet aerosolization).",
      "Deploy hydro-absorbent activated carbon spill pillow directly onto floating droplets.",
      "Set cabin ventilation in Node 2 to ISOLATED LOOP mode to prevent toxic formaldehyde vapor migration.",
      "Don emergency ocular goggles and organic vapor respirator cartridge.",
      "Place saturated spill pillow into hermetic hazardous waste canister HW-9 and torque seal to 45 N-m."
    ],
    "recovery_steps": [
      "Sample local atmosphere using Formaldehyde Draeger tube detector.",
      "Confirm cabin VOC levels are below 0.04 ppm before restoring normal ventilation."
    ]
  },
  {
    "id": "EMERG-03",
    "code": "CRYO-MELFI-LEAK",
    "title": "MELFI -80C Cryogenic Coolant Anomaly or Severe Cold Burn",
    "severity": "HIGH",
    "audio_alarm": "ALARM_CRYO_WARNING",
    "immediate_actions": [
      "If skin contact occurs: Immediately immerse affected skin in warm water (38C - 42C) from galley dispenser. DO NOT rub frozen tissue.",
      "If Stirling cycle coolant loop pressure drops below 1.5 bar: Close isolation valve CRYO-ISO-1.",
      "Don heavy cryogenic insulated gloves before touching any frosted valves or dewar latches."
    ],
    "recovery_steps": [
      "Report to medical officer for frostbite dressing application.",
      "Check sample integrity in Dewar cavities 1 through 4."
    ]
  },
  {
    "id": "EMERG-04",
    "code": "HAB-RAPID-DEPRESS",
    "title": "Cabin Rapid Depressurization Contingency (Pressure < 90 kPa)",
    "severity": "LIFE_CRITICAL",
    "audio_alarm": "ALARM_RAPID_DEPRESS",
    "immediate_actions": [
      "Cease ALL scientific experiments and power down non-vital hardware immediately.",
      "Follow umbilical guidance track toward Soyuz/Crew Dragon Return Vehicle.",
      "Don emergency pressure suits (IVA suits) and seal helmet visors.",
      "Identify and isolate leaking module hatch according to delta-P differential sensors."
    ],
    "recovery_steps": [
      "Execute hatch seal pressure integrity checklist.",
      "Coordinate with Mission Control Houston/ISRO MOX for orbital emergency repressurization."
    ]
  },
  {
    "id": "EMERG-05",
    "code": "BIOREACTOR-OVERPRESS",
    "title": "Cyanobacteria/Microalgae Photobioreactor Loop Overpressure (>150 kPa)",
    "severity": "MEDIUM",
    "audio_alarm": "ALARM_CAUTION_CHIME",
    "immediate_actions": [
      "Switch PBR peristaltic rotor pump to STANDBY.",
      "Open manual relief needle valve PRV-3 to bleed excess oxygen into secondary ballast bag.",
      "Verify loop pressure returns to nominal 115 - 125 kPa range.",
      "Inspect fluidic connections for rupture bulge or seal extrusion."
    ],
    "recovery_steps": [
      "Recalibrate pressure transducer PT-104.",
      "Resume cultivation at reduced 50% flow rate."
    ]
  }
]
