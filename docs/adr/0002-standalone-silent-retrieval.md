# Keep retrieval standalone and silent-first

The project implements its own headless, publisher-isolated retrieval engine instead of bundling or invoking InstSci. This preserves the original skill's silent-download identity and small composable surface, while borrowing only general coverage, detection, and verification lessons from public tools; users who need visible institutional workflows or MCP orchestration can install InstSci separately.
