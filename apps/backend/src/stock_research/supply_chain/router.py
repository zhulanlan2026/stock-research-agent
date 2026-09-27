import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.auth.dependencies import get_current_user
from stock_research.core.config import get_settings
from stock_research.iam.dependencies import require_permission
from stock_research.review.human_review import HumanReviewService
from stock_research.review.schemas import ReviewResponse
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session
from stock_research.supply_chain.alias import OrganizationAliasService
from stock_research.supply_chain.neo4j_client import Neo4jPublisher
from stock_research.supply_chain.risk_propagation import RiskPropagationService
from stock_research.supply_chain.risk_snapshot import RiskSnapshotStore
from stock_research.supply_chain.schemas import (
    GraphEdgeResponse,
    GraphResponse,
    OrganizationAliasCreate,
    OrganizationAliasResponse,
    RiskPropagationRequest,
    RiskPropagationResponse,
    RiskSnapshotCreate,
    RiskSnapshotResponse,
    SupplyChainContractCreate,
    SupplyChainContractResponse,
    SupplyChainReviewRequest,
    SymbolResolveResponse,
)
from stock_research.supply_chain.store import SupplyChainStore

router = APIRouter(prefix="/supply-chain", tags=["supply-chain"])
_require_review = require_permission("report.review")


@router.post(
    "/contracts",
    response_model=SupplyChainContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contract(
    body: SupplyChainContractCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SupplyChainContractResponse:
    contract = await SupplyChainStore(session).create_contract(
        tenant_id=current_user.tenant_id,
        subject_org=body.subject_org,
        object_org=body.object_org,
        amount=body.amount,
        currency=body.currency,
        valid_from=body.valid_from,
        valid_to=body.valid_to,
        evidence_ids=body.evidence_ids,
    )
    await session.commit()
    await session.refresh(contract)
    return SupplyChainContractResponse(
        id=contract.id,
        subject_org=contract.subject_org,
        object_org=contract.object_org,
        amount=contract.amount,
        currency=contract.currency,
        valid_from=contract.valid_from,
        valid_to=contract.valid_to,
        status=contract.status,
        evidence_ids=contract.evidence_ids,
    )


@router.get(
    "/contracts",
    response_model=list[SupplyChainContractResponse],
)
async def list_contracts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SupplyChainContractResponse]:
    contracts = await SupplyChainStore(session).list_contracts(
        tenant_id=current_user.tenant_id
    )
    return [
        SupplyChainContractResponse(
            id=contract.id,
            subject_org=contract.subject_org,
            object_org=contract.object_org,
            amount=contract.amount,
            currency=contract.currency,
            valid_from=contract.valid_from,
            valid_to=contract.valid_to,
            status=contract.status,
            evidence_ids=contract.evidence_ids,
        )
        for contract in contracts
    ]


@router.get(
    "/organization-aliases",
    response_model=list[OrganizationAliasResponse],
)
async def list_organization_aliases(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[OrganizationAliasResponse]:
    aliases = await OrganizationAliasService(session).list_aliases(
        tenant_id=current_user.tenant_id
    )
    return [
        OrganizationAliasResponse(
            id=alias.id,
            canonical_name=alias.canonical_name,
            alias=alias.alias,
        )
        for alias in aliases
    ]


@router.post(
    "/organization-aliases",
    response_model=OrganizationAliasResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization_alias(
    body: OrganizationAliasCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OrganizationAliasResponse:
    alias = await OrganizationAliasService(session).add_alias(
        tenant_id=current_user.tenant_id,
        canonical_name=body.canonical_name,
        alias=body.alias,
    )
    await session.commit()
    await session.refresh(alias)
    return OrganizationAliasResponse(
        id=alias.id,
        canonical_name=alias.canonical_name,
        alias=alias.alias,
    )


@router.get(
    "/resolve-symbol",
    response_model=SymbolResolveResponse,
)
async def resolve_symbol(
    symbol: str,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SymbolResolveResponse:
    organization = await OrganizationAliasService(session).resolve_symbol(symbol)
    return SymbolResolveResponse(symbol=symbol, organization=organization)


@router.delete(
    "/organization-aliases/{alias_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_organization_alias(
    alias_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await OrganizationAliasService(session).delete_alias(
        tenant_id=current_user.tenant_id,
        alias_id=alias_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ALIAS_NOT_FOUND", "message": "组织别名不存在"},
        )
    await session.commit()


@router.post(
    "/risk-propagation",
    response_model=RiskPropagationResponse,
)
async def propagate_risk(
    body: RiskPropagationRequest,
    _: User = Depends(get_current_user),
) -> RiskPropagationResponse:
    settings = get_settings()
    publisher = Neo4jPublisher(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
    )
    try:
        graph = publisher.list_graph()
    finally:
        publisher.close()

    risk = RiskPropagationService().propagate(
        list(graph.edges),
        body.initial_risk,
        damping=body.damping,
        max_steps=body.max_steps,
    )
    return RiskPropagationResponse(risk=risk)


@router.post(
    "/risk-snapshots",
    response_model=RiskSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_snapshot(
    body: RiskSnapshotCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RiskSnapshotResponse:
    settings = get_settings()
    publisher = Neo4jPublisher(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
    )
    try:
        graph = publisher.list_graph()
    finally:
        publisher.close()

    result = RiskPropagationService().propagate(
        list(graph.edges),
        body.initial_risk,
        damping=body.damping,
        max_steps=body.max_steps,
    )
    snapshot = await RiskSnapshotStore(session).create(
        tenant_id=current_user.tenant_id,
        symbol=body.symbol,
        initial_risk=body.initial_risk,
        max_steps=body.max_steps,
        damping=body.damping,
        result=result,
    )
    await session.commit()
    await session.refresh(snapshot)
    return RiskSnapshotResponse(
        id=snapshot.id,
        symbol=snapshot.symbol,
        initial_risk=snapshot.initial_risk,
        max_steps=snapshot.max_steps,
        damping=snapshot.damping,
        result=snapshot.result,
        created_at=snapshot.created_at,
    )


@router.get(
    "/risk-snapshots",
    response_model=list[RiskSnapshotResponse],
)
async def list_risk_snapshots(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[RiskSnapshotResponse]:
    snapshots = await RiskSnapshotStore(session).list(
        tenant_id=current_user.tenant_id
    )
    return [
        RiskSnapshotResponse(
            id=snapshot.id,
            symbol=snapshot.symbol,
            initial_risk=snapshot.initial_risk,
            max_steps=snapshot.max_steps,
            damping=snapshot.damping,
            result=snapshot.result,
            created_at=snapshot.created_at,
        )
        for snapshot in snapshots
    ]


@router.delete(
    "/risk-snapshots/{snapshot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_risk_snapshot(
    snapshot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await RiskSnapshotStore(session).delete(
        tenant_id=current_user.tenant_id,
        snapshot_id=snapshot_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SNAPSHOT_NOT_FOUND", "message": "风险快照不存在"},
        )
    await session.commit()


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    _: User = Depends(get_current_user),
) -> GraphResponse:
    settings = get_settings()
    try:
        publisher = Neo4jPublisher(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        try:
            data = publisher.list_graph()
        finally:
            publisher.close()
    except Exception:
        return GraphResponse(nodes=[], edges=[])

    return GraphResponse(
        nodes=data.nodes,
        edges=[
            GraphEdgeResponse(source=source, predicate=predicate, target=target)
            for source, predicate, target in data.edges
        ],
    )


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supply_chain_review(
    body: SupplyChainReviewRequest,
    current_user: User = Depends(_require_review),
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    review = await HumanReviewService(session).create(
        tenant_id=current_user.tenant_id,
        target_type="supply_chain_graph",
        target_id=body.symbol or "graph",
        reviewer_id=current_user.id,
    )
    await session.commit()
    return ReviewResponse.model_validate(review)
