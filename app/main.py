from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from app.database import engine, SessionLocal
from app import models
from app.langchain_service import SalesAnalyzer
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sales Analytics API",
    description="API for sales data analysis and insights",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for response validation
class TopProductResponse(BaseModel):
    product: str
    total_sold: int
    revenue: Optional[float] = None

class SalesInsightResponse(BaseModel):
    answer: str
    context_used: Optional[str] = None

# Dependency for database sessions
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logger.info("Database tables created/verified")

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    logger.info("Database engine disposed")

@app.get("/sales-insights", response_model=SalesInsightResponse)
async def sales_insights(
    question: str = Query(..., min_length=3, max_length=200, description="Your sales-related question"),
    days: int = Query(7, gt=0, le=365, description="Number of days of data to analyze")
):
    """
    Get AI-powered insights about sales data.
    
    Example questions:
    - "What are the top selling products?"
    - "Show me sales trends for last week"
    - "Which products need more promotion?"
    """
    try:
        analyzer = SalesAnalyzer()
        response = await analyzer.analyze_sales_question(question, days)
        return {"answer": response}
    except Exception as e:
        logger.error(f"Error in sales_insights: {e}")
        raise HTTPException(status_code=500, detail="Error processing your question")

@app.get("/top-products", response_model=List[TopProductResponse])
async def top_products(
    days: int = Query(30, gt=0, le=365, description="Analysis period in days"),
    limit: int = Query(5, gt=0, le=20, description="Number of top products to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top selling products by quantity sold in the specified period.
    Includes total revenue for each product.
    """
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(
                models.Product.name,
                func.sum(models.Sale.quantity).label("total_quantity"),
                func.sum(models.Sale.total_amount).label("total_revenue")
            )
            .join(models.Sale, models.Sale.product_id == models.Product.id)
            .where(models.Sale.sale_date >= start_date)
            .group_by(models.Product.name)
            .order_by(func.sum(models.Sale.quantity).desc())
            .limit(limit)
        )
        
        products = result.all()
        
        return [
            {
                "product": name,
                "total_sold": int(total_quantity),
                "revenue": round(float(total_revenue), 2)
            }
            for name, total_quantity, total_revenue in products
        ]
    except Exception as e:
        logger.error(f"Error in top_products: {e}")
        raise HTTPException(status_code=500, detail="Error fetching top products")

@app.get("/health")
async def health_check():
    """Service health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}