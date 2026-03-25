"""
Function Executor - Minimal executor for fast Pocket AI runtime.
Only keeps lightweight tool execution.
"""

from typing import Dict, Any


class FunctionExecutor:
    """Minimal executor for routed functions."""

    def __init__(self):
        pass

    def execute(self, func_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function and return structured result.

        Returns:
            {
                "success": bool,
                "message": str,
                "data": Any
            }
        """
        try:
            if func_name == "web_search":
                return self._web_search(params)
            elif func_name == "passthrough":
                return {
                    "success": True,
                    "message": "No tool execution needed.",
                    "data": {
                        "thinking": bool(params.get("thinking", False))
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Unknown function: {func_name}",
                    "data": None
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    def _web_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a web search."""
        query = params.get("query", "").strip()

        if not query:
            return {
                "success": False,
                "message": "No search query provided",
                "data": None
            }

        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            if results:
                formatted = []
                for result in results[:3]:
                    formatted.append(
                        {
                            "title": result.get("title", ""),
                            "body": result.get("body", "")[:200],
                            "url": result.get("href", "")
                        }
                    )

                return {
                    "success": True,
                    "message": f"Found {len(results)} results for '{query}'",
                    "data": {
                        "query": query,
                        "results": formatted
                    }
                }

            return {
                "success": True,
                "message": f"No results found for '{query}'",
                "data": {
                    "query": query,
                    "results": []
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Search failed: {e}",
                "data": None
            }


# Global instance
executor = FunctionExecutor()