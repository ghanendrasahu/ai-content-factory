import logging

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | %(levelname)s | "
        "service=ai-content-factory | %(name)s | %(message)s"
    ),
)

logger = logging.getLogger("ai-content-factory")
