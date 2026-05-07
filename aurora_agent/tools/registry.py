from .analytics import get_sales_statistics, get_top_products
from .base import ToolSpec
from .customers import get_top_customers, list_customers
from .delivery_notes import (
    analyze_stock_blockers,
    check_delivery_note_stock,
    get_delivery_note_detail,
    list_delivery_notes,
    prioritize_delivery_notes,
)
from .operations import count_customers, count_delivery_notes, count_low_stock_products, count_products, get_operational_summary, summarize_daily_operations
from .products import list_products
from .stock import get_product_movements, list_low_stock_products, list_out_of_stock_products


TOOLS = {
    "get_operational_summary": ToolSpec("get_operational_summary", "Resumen operativo del ERP.", get_operational_summary),
    "count_customers": ToolSpec("count_customers", "Cuenta clientes activos.", count_customers),
    "list_customers": ToolSpec("list_customers", "Lista clientes con filtros.", list_customers),
    "count_products": ToolSpec("count_products", "Cuenta productos activos.", count_products),
    "count_delivery_notes": ToolSpec("count_delivery_notes", "Cuenta albaranes registrados.", count_delivery_notes),
    "count_low_stock_products": ToolSpec("count_low_stock_products", "Cuenta productos con stock bajo.", count_low_stock_products),
    "list_delivery_notes": ToolSpec("list_delivery_notes", "Lista albaranes con filtros.", list_delivery_notes),
    "get_delivery_note_detail": ToolSpec("get_delivery_note_detail", "Detalle de un albaran.", get_delivery_note_detail),
    "check_delivery_note_stock": ToolSpec("check_delivery_note_stock", "Valida si un albaran es preparable por stock.", check_delivery_note_stock),
    "list_low_stock_products": ToolSpec("list_low_stock_products", "Lista productos con stock bajo.", list_low_stock_products),
    "list_out_of_stock_products": ToolSpec("list_out_of_stock_products", "Lista productos sin stock.", list_out_of_stock_products),
    "get_product_movements": ToolSpec("get_product_movements", "Movimientos recientes de un producto.", get_product_movements),
    "get_sales_statistics": ToolSpec("get_sales_statistics", "Metricas de ventas y estados.", get_sales_statistics),
    "get_top_products": ToolSpec("get_top_products", "Ranking de productos vendidos.", get_top_products),
    "get_top_customers": ToolSpec("get_top_customers", "Ranking de clientes por volumen.", get_top_customers),
    "analyze_stock_blockers": ToolSpec("analyze_stock_blockers", "Detecta bloqueos de stock en preparacion.", analyze_stock_blockers),
    "prioritize_delivery_notes": ToolSpec("prioritize_delivery_notes", "Prioriza albaranes pendientes.", prioritize_delivery_notes),
    "summarize_daily_operations": ToolSpec("summarize_daily_operations", "Resumen diario usando varias tools.", summarize_daily_operations),
    "list_products": ToolSpec("list_products", "Lista productos activos.", list_products),
}


def get_tool(name):
    return TOOLS.get(name)


def list_tool_specs():
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "read_only": spec.read_only,
            "required_permissions": list(spec.required_permissions),
            "max_results": spec.max_results,
        }
        for spec in TOOLS.values()
    ]
