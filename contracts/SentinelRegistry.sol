// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title SentinelRegistry
 * @notice On-chain registry for ArbiSense AI agent intelligence reports.
 *         The registered AI agent autonomously submits market analysis
 *         reports; each report is permanently recorded with its IPFS/data
 *         hash, timestamp, and a numeric risk/sentiment score.
 * @dev Deployed on Arbitrum Sepolia. Only the owner-registered agent wallet
 *      may submit reports; anyone may read them.
 */
contract SentinelRegistry {
    // ── Storage ──────────────────────────────────────────────────────────────

    address public owner;
    address public agent;

    struct Report {
        uint256 id;
        uint256 timestamp;
        string  dataHash;       // SHA-256 or IPFS CID of the full report JSON
        string  summary;        // ≤ 280-char human-readable summary
        uint8   sentimentScore; // 0 = extreme fear, 100 = extreme greed
        string  protocol;       // e.g. "uniswap-v3", "aave-v3", "gmx", "all"
    }

    Report[] private _reports;

    // ── Events ───────────────────────────────────────────────────────────────

    event AgentUpdated(address indexed previous, address indexed next);
    event ReportSubmitted(
        uint256 indexed id,
        address indexed submitter,
        uint256 timestamp,
        string  protocol,
        uint8   sentimentScore,
        string  dataHash
    );

    // ── Errors ───────────────────────────────────────────────────────────────

    error NotOwner();
    error NotAgent();
    error EmptyHash();
    error SummaryTooLong();
    error InvalidScore();

    // ── Constructor ──────────────────────────────────────────────────────────

    constructor(address _agent) {
        owner = msg.sender;
        agent = _agent;
        emit AgentUpdated(address(0), _agent);
    }

    // ── Modifiers ────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyAgent() {
        if (msg.sender != agent) revert NotAgent();
        _;
    }

    // ── Owner administration ──────────────────────────────────────────────────

    /**
     * @notice Transfer ownership to a new address.
     */
    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }

    /**
     * @notice Update the authorised agent wallet.
     *         Allows key rotation without redeploying.
     */
    function setAgent(address newAgent) external onlyOwner {
        emit AgentUpdated(agent, newAgent);
        agent = newAgent;
    }

    // ── Agent actions ─────────────────────────────────────────────────────────

    /**
     * @notice Submit a new market intelligence report.
     * @param dataHash      SHA-256 hex or IPFS CIDv1 of the full JSON report.
     * @param summary       Short description (≤ 280 chars).
     * @param sentimentScore 0–100 composite score (0 = fear, 100 = greed).
     * @param protocol      DeFi protocol identifier ("all", "uniswap-v3", …).
     */
    function submitReport(
        string calldata dataHash,
        string calldata summary,
        uint8           sentimentScore,
        string calldata protocol
    ) external onlyAgent returns (uint256 reportId) {
        if (bytes(dataHash).length == 0)         revert EmptyHash();
        if (bytes(summary).length > 280)          revert SummaryTooLong();
        if (sentimentScore > 100)                 revert InvalidScore();

        reportId = _reports.length;

        _reports.push(Report({
            id:             reportId,
            timestamp:      block.timestamp,
            dataHash:       dataHash,
            summary:        summary,
            sentimentScore: sentimentScore,
            protocol:       protocol
        }));

        emit ReportSubmitted(
            reportId,
            msg.sender,
            block.timestamp,
            protocol,
            sentimentScore,
            dataHash
        );
    }

    // ── Public read ───────────────────────────────────────────────────────────

    /**
     * @notice Total number of reports stored.
     */
    function reportCount() external view returns (uint256) {
        return _reports.length;
    }

    /**
     * @notice Retrieve a single report by ID.
     */
    function getReport(uint256 id) external view returns (Report memory) {
        require(id < _reports.length, "Report does not exist");
        return _reports[id];
    }

    /**
     * @notice Return the N most recent reports (latest first).
     * @param n Maximum number of reports to return.
     */
    function latestReports(uint256 n) external view returns (Report[] memory out) {
        uint256 total = _reports.length;
        if (n > total) n = total;
        out = new Report[](n);
        for (uint256 i = 0; i < n; i++) {
            out[i] = _reports[total - 1 - i];
        }
    }

    /**
     * @notice Filter reports by protocol string (exact match).
     * @param protocol  Protocol identifier to filter by.
     * @param maxReturn Maximum number of results.
     */
    function reportsByProtocol(
        string calldata protocol,
        uint256 maxReturn
    ) external view returns (Report[] memory out) {
        uint256 total = _reports.length;
        // Two-pass: count matches, then fill.
        uint256 count;
        for (uint256 i = 0; i < total && count < maxReturn; i++) {
            if (_strEq(_reports[i].protocol, protocol)) count++;
        }
        out = new Report[](count);
        uint256 idx;
        for (uint256 i = 0; i < total && idx < count; i++) {
            if (_strEq(_reports[i].protocol, protocol)) {
                out[idx++] = _reports[i];
            }
        }
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    function _strEq(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
