from datetime import datetime, timedelta
from typing import List, Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI  # or another LLM
from app.database import SessionLocal
from app.models import Sale, Product
import logging

# Configure logging
logger = logging.getLogger(__name__)

class SalesAnalyzer:
    def __init__(self):
        # Consider making LLM configurable via environment variables
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo"  # Specify model explicitly
        )
        
        self.prompt_template = PromptTemplate(
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
            
            Dados de vendas da última semana:
            {context}
            
            Resposta:
            """
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)

    async def _get_recent_sales_data(self, days: int = 7) -> List[Tuple[Sale, Product]]:
        """Fetch sales data from the last N days with product information"""
        async with SessionLocal() as session:
            try:
                last_week = datetime.now() - timedelta(days=days)
                result = await session.execute(
                    select(Sale, Product)
                    .join(Product, Sale.product_id == Product.id)
                    .where(Sale.sale_date >= last_week)
                    .order_by(Sale.sale_date.desc())  # Most recent first
                )
                return result.all()
            except Exception as e:
                logger.error(f"Error fetching sales data: {e}")
                raise

    def _format_sales_context(self, sales_data: List[Tuple[Sale, Product]]) -> str:
        """Format sales data into a readable context string"""
        if not sales_data:
            return "Nenhuma venda registrada na última semana."
            
        context_lines = []
        for sale, product in sales_data:
            context_lines.append(
                f"- {product.name}: {sale.quantity} unid. (R${sale.total_amount:.2f}) "
                f"em {sale.sale_date.strftime('%d/%m/%Y %H:%M')}"
            )
        return "\n".join(context_lines)

    async def analyze_sales_question(self, question: str) -> str:
        """Process a sales-related question with recent data"""
        try:
            # Get data
            sales_data = await self._get_recent_sales_data()
            
            # Format context
            context = self._format_sales_context(sales_data)
            logger.debug(f"Generated context: {context}")
            
            # Get LLM response
            response = await self.chain.arun(
                question=question,
                context=context
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação."

# Example usage:
# analyzer = SalesAnalyzer()
# response = await analyzer.analyze_sales_question("Quais foram os produtos mais vendidos?")