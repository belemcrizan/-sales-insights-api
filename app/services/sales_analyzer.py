from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from app.database import SessionLocal
from app.models import Sale, Product
import logging
import os
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class SalesAnalyzer:
    def __init__(self):
        self._initialize_llm()
        self.chain = self._create_analysis_chain()

    def _initialize_llm(self):
        """Initialize the LLM with configuration"""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.critical("OPENAI_API_KEY environment variable not configured")
            raise RuntimeError("OpenAI API key not configured")
            
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo",
            openai_api_key=openai_api_key
        )

    def _create_analysis_chain(self) -> LLMChain:
        """Create the LLM analysis chain"""
        prompt_template = PromptTemplate(
            input_variables=["question", "context"],
            template="""
            Você é um especialista em análise de vendas. 
            Responda à pergunta com base estritamente nos dados fornecidos.
            
            Diretrizes:
            1. Seja conciso e preciso
            2. Formate números e datas claramente
            3. Se não houver dados relevantes, informe "Não há dados suficientes"
            4. Nunca invente informações
            
            Pergunta: {question}
            
            Dados de vendas do período:
            {context}
            
            Resposta:
            """
        )
        return LLMChain(llm=self.llm, prompt=prompt_template)

    async def _get_sales_data(self, days: int) -> List[Tuple[Sale, Product]]:
        """Fetch sales data from the last N days with product information"""
        async with SessionLocal() as session:
            try:
                start_date = datetime.now() - timedelta(days=days)
                result = await session.execute(
                    select(Sale, Product)
                    .join(Product, Sale.product_id == Product.id)
                    .where(Sale.sale_date >= start_date)
                    .order_by(Sale.sale_date.desc())
                )
                return result.all()
            except Exception as e:
                logger.error(f"Database error: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erro ao acessar dados históricos de vendas"
                )

    def _format_context(self, sales_data: List[Tuple[Sale, Product]]) -> str:
        """Format sales data into a readable context string"""
        if not sales_data:
            return "Nenhuma venda registrada no período solicitado."
            
        return "\n".join(
            f"- {product.name}: {sale.quantity} unid. (R${sale.total_amount:.2f}) "
            f"em {sale.sale_date.strftime('%d/%m/%Y %H:%M')}"
            for sale, product in sales_data
        )

    async def analyze_sales(self, question: str, days: int = 7) -> Dict[str, str]:
        """
        Analyze sales data and generate insights
        
        Args:
            question: The question to analyze
            days: Number of days to look back (default: 7)
            
        Returns:
            Dictionary with 'answer' and 'context_used' keys
            
        Raises:
            HTTPException: For operational errors
        """
        try:
            sales_data = await self._get_sales_data(days)
            context = self._format_context(sales_data)
            logger.info(f"Analyzing question: {question} with {len(sales_data)} records")
            
            response = await self.chain.arun(
                question=question,
                context=context
            )
            
            return {
                "answer": response.strip(),
                "context_used": context
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar insights de vendas"
            )