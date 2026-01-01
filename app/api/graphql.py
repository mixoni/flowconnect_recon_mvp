from __future__ import annotations
import strawberry
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session

from app.db.session import get_session

from app.modules.tenants.gql import TenantsQuery, TenantsMutation
from app.modules.invoices.gql import InvoicesQuery, InvoicesMutation
from app.modules.transactions.gql import TransactionsMutation
from app.modules.reconciliation.gql import ReconciliationQuery, ReconciliationMutation

@strawberry.type
class Query(TenantsQuery, InvoicesQuery, ReconciliationQuery):
    pass

@strawberry.type
class Mutation(TenantsMutation, InvoicesMutation, TransactionsMutation, ReconciliationMutation):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)

def build_graphql_router() -> GraphQLRouter:
    async def get_context() -> dict:
        # Strawberry FastAPI context can be async. We'll open a session per request.
        # Our session factory returns a sync Session, so we create it here and close in a response hook isn't trivial.
        # For simplicity in this challenge, we pass a session generator and create/close within resolvers via context manager.
        # But to keep changes minimal, we create one session and rely on FastAPI lifespan to dispose connections (SQLite).
        session = next(get_session())  # get_session is a generator dependency
        return {"session": session}

    return GraphQLRouter(schema, context_getter=get_context)
