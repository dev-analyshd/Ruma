// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * RUMAHeartbeat — On-Chain Cognitive State Journal
 * ================================================
 * Records RUMA's live cognitive metrics (Ψ, Λ, IQ, gate status)
 * to BSC every 10 minutes. Creates an immutable developmental
 * history of the agent's intelligence and coherence over time.
 *
 * Deploy: scripts/deploy_contracts.py
 * Set env: RUMA_HEARTBEAT_CONTRACT=<deployed_address>
 */
contract RUMAHeartbeat {

    // ── Storage ───────────────────────────────────────────────────────────────

    struct HeartbeatRecord {
        uint256 timestamp;
        address agent;
        uint32  psi_x10000;     // Ψ × 10000  (e.g. 6721 = Ψ 0.6721)
        uint32  delta_x10000;   // Δ × 10000  (dynamic threshold)
        uint32  lambda_x1e6;    // Λ × 1000000 (moat score)
        uint16  iq;             // IQ 0–200
        bool    gate_open;      // was the coherence gate open?
        bytes32 cycle_id;       // keccak256 fingerprint of the decision cycle
    }

    HeartbeatRecord[] public records;
    mapping(address => uint256[]) public agentRecordIds;

    // ── Events ────────────────────────────────────────────────────────────────

    event HeartbeatEmitted(
        address indexed agent,
        uint256 indexed recordId,
        uint32  psi_x10000,
        uint32  lambda_x1e6,
        uint16  iq,
        bool    gate_open
    );

    // ── Write ─────────────────────────────────────────────────────────────────

    /**
     * @notice Record a cognitive heartbeat for this agent.
     * @param psi_x10000    Ψ score × 10000 (e.g. pass 6721 for Ψ=0.6721)
     * @param delta_x10000  Δ threshold × 10000
     * @param lambda_x1e6   Λ moat × 1 000 000
     * @param iq            IQ 0–200
     * @param gate_open     True if Ψ ≥ Δ (gate opened this cycle)
     * @param cycle_id      keccak256 of cycle fingerprint string
     */
    function emitHeartbeat(
        uint32  psi_x10000,
        uint32  delta_x10000,
        uint32  lambda_x1e6,
        uint16  iq,
        bool    gate_open,
        bytes32 cycle_id
    ) external {
        uint256 id = records.length;
        records.push(HeartbeatRecord({
            timestamp:    block.timestamp,
            agent:        msg.sender,
            psi_x10000:   psi_x10000,
            delta_x10000: delta_x10000,
            lambda_x1e6:  lambda_x1e6,
            iq:           iq,
            gate_open:    gate_open,
            cycle_id:     cycle_id
        }));
        agentRecordIds[msg.sender].push(id);
        emit HeartbeatEmitted(msg.sender, id, psi_x10000, lambda_x1e6, iq, gate_open);
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    function getRecord(uint256 id) external view returns (HeartbeatRecord memory) {
        require(id < records.length, "Record does not exist");
        return records[id];
    }

    function getLatestAgentRecord(address agent) external view returns (HeartbeatRecord memory) {
        uint256[] storage ids = agentRecordIds[agent];
        require(ids.length > 0, "No records for this agent");
        return records[ids[ids.length - 1]];
    }

    function getAgentRecordCount(address agent) external view returns (uint256) {
        return agentRecordIds[agent].length;
    }

    function getAgentRecordIds(address agent) external view returns (uint256[] memory) {
        return agentRecordIds[agent];
    }

    function totalRecords() external view returns (uint256) {
        return records.length;
    }
}
