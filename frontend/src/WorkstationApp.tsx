import React, { useState } from "react";

export interface ProvenanceItem {
    granule_id: string;
    product_type: "GCOV" | "GUNW" | "GOFF" | "SME2";
    acquisition_start: string;
    acquisition_end: string;
    track_number: number;
    frame_number: number;
    look_direction: string;
    orbit_pass_direction: string;
    composite_release_id: string;
    maturity: "VALIDATED" | "PROVISIONAL" | "BETA";
}

export interface ChangeMeasurementRecord {
    id: string;
    study_area_id: string;
    region_name: string;
    coordinates_wgs84: [number, number];
    measurement_type: string;
    value: number | null;
    unit: "dB" | "mm";
    uncertainty: number | null;
    quality_status: "high" | "moderate" | "low" | "invalid";
    coherence_or_looks: number | null;
    apof_disagreement_mm?: number | null;
    sign_convention: string;
    source_observations: ProvenanceItem[];
    supporting_context: Record<string, string>;
    limitations: string[];
}

export interface InterpretationResponse {
    change_result_id: string;
    what_changed: string;
    where_and_when: string;
    measurement_and_reliability: string;
    meca_attribution_class: string;
    cautious_interpretation: string;
    cited_granules: string[];
    limitations: string[];
}

const QUALITY_BADGE_STYLES: Record<ChangeMeasurementRecord["quality_status"], React.CSSProperties> = {
    high: { backgroundColor: "#DCFCE7", color: "#166534", border: "1px solid #86EFAC" },
    moderate: { backgroundColor: "#FEF9C3", color: "#854D0E", border: "1px solid #FDE047" },
    low: { backgroundColor: "#FFEDD5", color: "#9A3412", border: "1px solid #FDBA74" },
    invalid: { backgroundColor: "#FEE2E2", color: "#991B1B", border: "1px solid #FCA5A5" },
};

export const WorkstationApp: React.FC<{
    selectedRecord: ChangeMeasurementRecord | null;
    interpretation: InterpretationResponse | null;
    onRequestInterpretation: (rec: ChangeMeasurementRecord) => void;
}> = ({ selectedRecord, interpretation, onRequestInterpretation }) => {
    const [activeLayer, setActiveLayer] = useState<"measurement" | "uncertainty" | "quality">("measurement");

    return (
        <div
            style={{
                display: "grid",
                gridTemplateRows: "56px 1fr 88px",
                height: "100vh",
                backgroundColor: "#F8FAFC",
                color: "#0F172A",
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            }}
        >
            {/* Top Header */}
            <header
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0 20px",
                    backgroundColor: "#FFFFFF",
                    borderBottom: "1px solid #E2E8F0",
                }}
            >
                <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
                    <strong style={{ fontSize: "18px", letterSpacing: "0.04em" }}>TERRAVOX</strong>
                    <span style={{ fontSize: "12px", color: "#475569", fontWeight: 500 }}>
                        NASA-ISRO NISAR EARTH SURFACE INTELLIGENCE WORKSTATION
                    </span>
                </div>
                <div style={{ fontSize: "12px", color: "#334155" }}>
                    Data Rule: Genuine NISAR L2 Observations Only · Uncertainty & Masking Enforced
                </div>
            </header>

            {/* Main 3-Column Scientific Workstation */}
            <main
                style={{
                    display: "grid",
                    gridTemplateColumns: "300px 1fr 400px",
                    overflow: "hidden",
                }}
            >
                {/* Left Panel: Study Area, Products & Layer Controls */}
                <aside
                    style={{
                        backgroundColor: "#FFFFFF",
                        borderRight: "1px solid #E2E8F0",
                        padding: "16px",
                        overflowY: "auto",
                    }}
                >
                    <h3 style={{ fontSize: "13px", textTransform: "uppercase", color: "#475569", marginTop: 0 }}>
                        1. Study Area & Data Layer
                    </h3>
                    <div style={{ marginBottom: "16px" }}>
                        <label style={{ fontSize: "12px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                            Active Scientific Layer
                        </label>
                        {(["measurement", "uncertainty", "quality"] as const).map((layer) => (
                            <button
                                key={layer}
                                onClick={() => setActiveLayer(layer)}
                                style={{
                                    display: "block",
                                    width: "100%",
                                    textAlign: "left",
                                    padding: "8px 10px",
                                    marginBottom: "6px",
                                    borderRadius: "4px",
                                    border: activeLayer === layer ? "1px solid #0284C7" : "1px solid #CBD5E1",
                                    backgroundColor: activeLayer === layer ? "#F0F9FF" : "#FFFFFF",
                                    fontSize: "13px",
                                    cursor: "pointer",
                                }}
                            >
                                {layer === "measurement" && "Primary Radar Measurement (Δγ⁰ dB / LOS mm)"}
                                {layer === "uncertainty" && "UARI Measurement Uncertainty (±σ)"}
                                {layer === "quality" && "Validity & Quality Category Mask"}
                            </button>
                        ))}
                    </div>

                    <h3 style={{ fontSize: "13px", textTransform: "uppercase", color: "#475569" }}>
                        2. Source Provenance (HDF5)
                    </h3>
                    {selectedRecord ? (
                        selectedRecord.source_observations.map((obs) => (
                            <div
                                key={obs.granule_id}
                                style={{
                                    padding: "10px",
                                    backgroundColor: "#F8FAFC",
                                    border: "1px solid #E2E8F0",
                                    borderRadius: "4px",
                                    fontSize: "12px",
                                    marginBottom: "8px",
                                }}
                            >
                                <div style={{ fontWeight: 600, wordBreak: "break-all" }}>{obs.granule_id}</div>
                                <div>Product: NISAR L2 {obs.product_type} ({obs.maturity})</div>
                                <div>Track / Frame: {obs.track_number} / {obs.frame_number} ({obs.orbit_pass_direction})</div>
                                <div>Look Direction: {obs.look_direction}</div>
                                <div>CRID Baseline: {obs.composite_release_id}</div>
                            </div>
                        ))
                    ) : (
                        <p style={{ fontSize: "12px", color: "#64748B" }}>
                            Load a verified NISAR product and click a location on the map to inspect provenance.
                        </p>
                    )}
                </aside>

                {/* Center Panel: MapLibre GL Container */}
                <section style={{ position: "relative", backgroundColor: "#E2E8F0" }}>
                    <div
                        id="terravox-map-container"
                        style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}
                    >
                        {/* MapLibre GL JS binds to #terravox-map-container */}
                        <span style={{ fontSize: "13px", color: "#475569" }}>
                            MapLibre GL JS Scientific Canvas — Active Layer: <strong>{activeLayer.toUpperCase()}</strong>
                        </span>
                    </div>
                </section>

                {/* Right Panel: Evidence, UARI Confidence & Grounded Interpreter */}
                <aside
                    style={{
                        backgroundColor: "#FFFFFF",
                        borderLeft: "1px solid #E2E8F0",
                        padding: "16px",
                        overflowY: "auto",
                    }}
                >
                    <h3 style={{ fontSize: "13px", textTransform: "uppercase", color: "#475569", marginTop: 0 }}>
                        3. Evidence & Confidence Center
                    </h3>

                    {!selectedRecord ? (
                        <p style={{ fontSize: "13px", color: "#64748B" }}>
                            Select a pixel or changed feature on the map to inspect its NISAR measurement, UARI uncertainty, and limitations.
                        </p>
                    ) : (
                        <>
                            <div
                                style={{
                                    padding: "12px",
                                    border: "1px solid #E2E8F0",
                                    borderRadius: "6px",
                                    marginBottom: "14px",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                    <span style={{ fontSize: "12px", color: "#475569" }}>{selectedRecord.measurement_type}</span>
                                    <span
                                        style={{
                                            ...QUALITY_BADGE_STYLES[selectedRecord.quality_status],
                                            fontSize: "11px",
                                            fontWeight: 600,
                                            padding: "2px 8px",
                                            borderRadius: "999px",
                                            textTransform: "uppercase",
                                        }}
                                    >
                                        {selectedRecord.quality_status} reliability
                                    </span>
                                </div>

                                <div style={{ fontSize: "24px", fontWeight: 700, margin: "8px 0 4px" }}>
                                    {selectedRecord.value !== null
                                        ? `${selectedRecord.value >= 0 ? "+" : ""}${selectedRecord.value.toFixed(2)} ${selectedRecord.unit}`
                                        : "Masked / Invalid Pixel"}
                                </div>

                                <div style={{ fontSize: "12px", color: "#334155" }}>
                                    Uncertainty (1σ):{" "}
                                    <strong>
                                        {selectedRecord.uncertainty !== null
                                            ? `± ${selectedRecord.uncertainty.toFixed(2)} ${selectedRecord.unit}`
                                            : "N/A"}
                                    </strong>
                                </div>

                                <div style={{ fontSize: "11px", color: "#64748B", marginTop: "6px" }}>
                                    {selectedRecord.sign_convention}
                                </div>
                            </div>

                            <button
                                onClick={() => onRequestInterpretation(selectedRecord)}
                                style={{
                                    width: "100%",
                                    padding: "9px 12px",
                                    backgroundColor: "#0F172A",
                                    color: "#FFFFFF",
                                    border: "none",
                                    borderRadius: "4px",
                                    fontSize: "13px",
                                    fontWeight: 600,
                                    cursor: "pointer",
                                    marginBottom: "14px",
                                }}
                            >
                                Generate Evidence-Grounded Explanation
                            </button>

                            {interpretation && (
                                <div
                                    style={{
                                        padding: "12px",
                                        backgroundColor: "#F8FAFC",
                                        border: "1px solid #CBD5E1",
                                        borderRadius: "6px",
                                        fontSize: "12.5px",
                                        lineHeight: 1.5,
                                    }}
                                >
                                    <div style={{ fontWeight: 700, marginBottom: "6px", color: "#0F172A" }}>
                                        MECA Class: {interpretation.meca_attribution_class}
                                    </div>
                                    <p style={{ margin: "0 0 8px" }}>
                                        <strong>What was observed:</strong> {interpretation.what_changed}
                                    </p>
                                    <p style={{ margin: "0 0 8px" }}>
                                        <strong>Where & When:</strong> {interpretation.where_and_when}
                                    </p>
                                    <p style={{ margin: "0 0 8px" }}>
                                        <strong>Cautious Interpretation:</strong> {interpretation.cautious_interpretation}
                                    </p>
                                    <div style={{ marginTop: "10px" }}>
                                        <strong>Known Scientific Limitations:</strong>
                                        <ul style={{ margin: "4px 0 0", paddingLeft: "18px" }}>
                                            {interpretation.limitations.map((lim, i) => (
                                                <li key={i}>{lim}</li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </aside>
            </main>

            {/* Bottom Panel: Change Time Machine Controls */}
            <footer
                style={{
                    backgroundColor: "#FFFFFF",
                    borderTop: "1px solid #E2E8F0",
                    padding: "12px 20px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                }}
            >
                <div>
                    <strong style={{ fontSize: "12px", display: "block" }}>CHANGE TIME MACHINE</strong>
                    <span style={{ fontSize: "11px", color: "#64748B" }}>
                        Only compatible NISAR acquisitions (matching track, frame, look direction, and CRID) are enabled.
                    </span>
                </div>
                <div style={{ fontSize: "12px", color: "#1E293B" }}>
                    {selectedRecord && selectedRecord.source_observations.length > 0
                        ? selectedRecord.source_observations
                            .map((o) => `${o.acquisition_start.slice(0, 10)} (${o.product_type})`)
                            .join("  →  ")
                        : "Awaiting verified NISAR stack selection"}
                </div>
            </footer>
        </div>
    );
};