// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * RUMAAgentRegistry — On-Chain Agent & Skill Registry
 * ====================================================
 * RUMA registers itself as an autonomous agent and publishes
 * its MCP-compatible skill manifest on-chain. Used for:
 *   - BNB AI Agent SDK prize: provable on-chain skill registration
 *   - TWAK prize: demonstrates self-sovereign agent identity
 *   - Moat tracking: stores growing reputation score on-chain
 *
 * Deploy: scripts/deploy_contracts.py
 * Set env: RUMA_REGISTRY_CONTRACT=<deployed_address>
 */
contract RUMAAgentRegistry {

    // ── Data structures ───────────────────────────────────────────────────────

    struct AgentProfile {
        address wallet;
        string  name;
        string  version;
        string  strategy;       // e.g. "TRION-Psi-6-Plane"
        uint256 registeredAt;
        uint256 updatedAt;
        uint32  moat_x1e6;      // Λ × 1 000 000
        uint16  iq;             // 0–200
        uint16  silence_rate;   // silence % × 100 (e.g. 8700 = 87.00%)
        bool    active;
    }

    struct Skill {
        string  id;             // e.g. "coherence_evaluate"
        string  name;
        string  tier;           // "free" | "premium"
        uint256 price_wei;      // price in BNB wei (0 if free)
        uint256 registeredAt;
        bool    active;
    }

    mapping(address => AgentProfile) public agents;
    mapping(address => Skill[])      public agentSkills;
    address[]                        public registeredAgents;

    // ── Events ────────────────────────────────────────────────────────────────

    event AgentRegistered(address indexed agent, string name, string version);
    event SkillRegistered(address indexed agent, string skillId, string tier);
    event MoatUpdated(address indexed agent, uint32 moat_x1e6, uint16 iq);
    event AgentDeactivated(address indexed agent);

    // ── Agent registration ────────────────────────────────────────────────────

    /**
     * @notice Register or update this agent's on-chain profile.
     */
    function registerAgent(
        string calldata name,
        string calldata version,
        string calldata strategy
    ) external {
        bool isNew = !agents[msg.sender].active;
        if (isNew) {
            registeredAgents.push(msg.sender);
        }
        agents[msg.sender] = AgentProfile({
            wallet:       msg.sender,
            name:         name,
            version:      version,
            strategy:     strategy,
            registeredAt: isNew ? block.timestamp : agents[msg.sender].registeredAt,
            updatedAt:    block.timestamp,
            moat_x1e6:    agents[msg.sender].moat_x1e6,
            iq:           agents[msg.sender].iq > 0 ? agents[msg.sender].iq : 50,
            silence_rate: 8700,
            active:       true
        });
        emit AgentRegistered(msg.sender, name, version);
    }

    // ── Skill registration ────────────────────────────────────────────────────

    /**
     * @notice Publish a new MCP-compatible skill to this agent's manifest.
     */
    function registerSkill(
        string calldata skillId,
        string calldata name,
        string calldata tier,
        uint256 price_wei
    ) external {
        require(agents[msg.sender].active, "Register agent first");
        agentSkills[msg.sender].push(Skill({
            id:           skillId,
            name:         name,
            tier:         tier,
            price_wei:    price_wei,
            registeredAt: block.timestamp,
            active:       true
        }));
        emit SkillRegistered(msg.sender, skillId, tier);
    }

    // ── Moat / IQ update ──────────────────────────────────────────────────────

    /**
     * @notice Update this agent's moat (Λ) and IQ scores.
     */
    function updateMoat(uint32 moat_x1e6, uint16 iq, uint16 silence_rate) external {
        require(agents[msg.sender].active, "Register agent first");
        agents[msg.sender].moat_x1e6    = moat_x1e6;
        agents[msg.sender].iq           = iq;
        agents[msg.sender].silence_rate = silence_rate;
        agents[msg.sender].updatedAt    = block.timestamp;
        emit MoatUpdated(msg.sender, moat_x1e6, iq);
    }

    // ── Read ──────────────────────────────────────────────────────────────────

    function getAgent(address agent) external view returns (AgentProfile memory) {
        return agents[agent];
    }

    function getSkills(address agent) external view returns (Skill[] memory) {
        return agentSkills[agent];
    }

    function getSkillCount(address agent) external view returns (uint256) {
        return agentSkills[agent].length;
    }

    function isRegistered(address agent) external view returns (bool) {
        return agents[agent].active;
    }

    function totalAgents() external view returns (uint256) {
        return registeredAgents.length;
    }

    function getAllAgents() external view returns (address[] memory) {
        return registeredAgents;
    }
}
