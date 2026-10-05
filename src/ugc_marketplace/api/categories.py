"""
Categories API endpoints for UGC Marketplace.

Provides CRUD operations for product/service categories with pagination
and input validation.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ugc_marketplace.security.auth import get_current_user, require_auth
from ugc_marketplace.security.authorization import Permission, require_permission

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


# ─── Pydantic Schemas ────────────────────────────────────────────────────────


class CategoryBase(BaseModel):
    """Shared category fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Category display name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=120,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-friendly identifier",
    )
    description: str | None = Field(None, max_length=500)
    parent_id: int | None = Field(None, description="Parent category ID for nesting")
    icon: str | None = Field(None, max_length=200, description="Icon URL or emoji")
    is_active: bool = Field(True)
    sort_order: int = Field(0, ge=0, le=9999)


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""

    pass


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=500)
    parent_id: int | None = None
    icon: str | None = Field(None, max_length=200)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0, le=9999)


class CategoryResponse(CategoryBase):
    """Full category representation returned by the API."""

    id: int
    created_at: datetime
    updated_at: datetime
    product_count: int = 0

    class Config:
        from_attributes = True


class PaginatedCategoryResponse(BaseModel):
    """Paginated list wrapper."""

    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Mock Data Store ─────────────────────────────────────────────────────────

MOCK_CATEGORIES: list[dict] = [
    {
        "id": 1,
        "name": "Digital Products",
        "slug": "digital-products",
        "description": "Software, templates, and digital downloads",
        "parent_id": None,
        "icon": "💻",
        "is_active": True,
        "sort_order": 1,
        "created_at": datetime(2025, 1, 15, 10, 30, 0),
        "updated_at": datetime(2025, 6, 20, 14, 0, 0),
        "product_count": 142,
    },
    {
        "id": 2,
        "name": "Graphic Design",
        "slug": "graphic-design",
        "description": "Logos, branding, illustrations, and visual assets",
        "parent_id": None,
        "icon": "🎨",
        "is_active": True,
        "sort_order": 2,
        "created_at": datetime(2025, 1, 15, 10, 35, 0),
        "updated_at": datetime(2025, 7, 1, 9, 15, 0),
        "product_count": 89,
    },
    {
        "id": 3,
        "name": "Video & Animation",
        "slug": "video-animation",
        "description": "Stock footage, motion graphics, and animated content",
        "parent_id": None,
        "icon": "🎬",
        "is_active": True,
        "sort_order": 3,
        "created_at": datetime(2025, 1, 20, 8, 0, 0),
        "updated_at": datetime(2025, 5, 10, 11, 45, 0),
        "product_count": 67,
    },
    {
        "id": 4,
        "name": "Writing & Content",
        "slug": "writing-content",
        "description": "Articles, copywriting, and editorial services",
        "parent_id": None,
        "icon": "✍️",
        "is_active": True,
        "sort_order": 4,
        "created_at": datetime(2025, 2, 1, 12, 0, 0),
        "updated_at": datetime(2025, 8, 12, 16, 30, 0),
        "product_count": 54,
    },
    {
        "id": 5,
        "name": "Music & Audio",
        "slug": "music-audio",
        "description": "Royal tracks, sound effects, and audio production",
        "parent_id": None,
        "icon": "🎵",
        "is_active": True,
        "sort_order": 5,
        "created_at": datetime(2025, 2, 10, 9, 0, 0),
        "updated_at": datetime(2025, 4, 22, 13, 0, 0),
        "product_count": 38,
    },
    {
        "id": 6,
        "name": "UI/UX Design",
        "slug": "ui-ux-design",
        "description": "Interface design, wireframes, and user experience assets",
        "parent_id": 2,
        "icon": "📱",
        "is_active": True,
        "sort_order": 6,
        "created_at": datetime(2025, 3, 5, 14, 20, 0),
        "updated_at": datetime(2025, 9, 1, 10, 0, 0),
        "product_count": 73,
    },
    {
        "id": 7,
        "name": "3D Models",
        "slug": "3d-models",
        "description": "3D assets, characters, environments, and printable models",
        "parent_id": None,
        "icon": "🧊",
        "is_active": True,
        "sort_order": 7,
        "created_at": datetime(2025, 3, 15, 11, 0, 0),
        "updated_at": datetime(2025, 6, 30, 8, 45, 0),
        "product_count": 45,
    },
    {
        "id": 8,
        "name": "Photography",
        "slug": "photography",
        "description": "Stock photos, presets, and editing services",
        "parent_id": None,
        "icon": "📷",
        "is_active": True,
        "sort_order": 8,
        "created_at": datetime(2025, 4, 1, 10, 0, 0),
        "updated_at": datetime(2025, 7, 18, 15, 30, 0),
        "product_count": 112,
    },
    {
        "id": 9,
        "name": "Web Development",
        "slug": "web-development",
        "description": "Themes, plugins, scripts, and development services",
        "parent_id": None,
        "icon": "🌐",
        "is_active": True,
        "sort_order": 9,
        "created_at": datetime(2025, 4, 20, 9, 30, 0),
        "updated_at": datetime(2025, 8, 5, 12, 0, 0),
        "product_count": 96,
    },
    {
        "id": 10,
        "name": "Marketing & Ads",
        "slug": "marketing-ads",
        "description": "Ad creatives, campaign assets, and marketing templates",
        "parent_id": None,
        "icon": "📣",
        "is_active": False,
        "sort_order": 10,
        "created_at": datetime(2025, 5, 1, 8, 0, 0),
        "updated_at": datetime(2025, 5, 1, 8, 0, 0),
        "product_count": 21,
    },
    {
        "id": 11,
        "name": "Icon Sets",
        "slug": "icon-sets",
        "description": "Custom icon packs and vector icon libraries",
        "parent_id": 2,
        "icon": "🔣",
        "is_active": True,
        "sort_order": 11,
        "created_at": datetime(2025, 5, 15, 13, 0, 0),
        "updated_at": datetime(2025, 9, 10, 17, 0, 0),
        "product_count": 33,
    },
    {
        "id": 12,
        "name": "Fonts & Typography",
        "slug": "fonts-typography",
        "description": "Custom fonts, typefaces, and lettering assets",
        "parent_id": None,
        "icon": "🔤",
        "is_active": True,
        "sort_order": 12,
        "created_at": datetime(2025, 6, 1, 10, 0, 0),
        "updated_at": datetime(2025, 10, 1, 9, 0, 0),
        "product_count": 58,
    },
]

_next_id = max(c["id"] for c in MOCK_CATEGORIES) + 1


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _get_category_or_404(category_id: int) -> dict:
    """Return category dict or raise 404."""
    for cat in MOCK_CATEGORIES:
        if cat["id"] == category_id:
            return cat
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Category with id {category_id} not found",
    )


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedCategoryResponse,
    summary="List categories",
    description="Retrieve a paginated list of categories with optional filtering.",
)
async def list_categories(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Filter by name or slug (case-insensitive)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    parent_id: int | None = Query(None, description="Filter by parent category ID"),
    user=Depends(require_permission(Permission.CATEGORY_READ)),
) -> PaginatedCategoryResponse:
    """
    Return a paginated list of categories.

    Supports filtering by search term, active status, and parent category.
    Results are ordered by sort_order ascending, then by name.
    """
    filtered = MOCK_CATEGORIES.copy()

    if search:
        term = search.lower()
        filtered = [c for c in filtered if term in c["name"].lower() or term in c["slug"].lower()]

    if is_active is not None:
        filtered = [c for c in filtered if c["is_active"] == is_active]

    if parent_id is not None:
        filtered = [c for c in filtered if c["parent_id"] == parent_id]

    # Sort by sort_order, then name
    filtered.sort(key=lambda c: (c["sort_order"], c["name"]))

    total = len(filtered)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return PaginatedCategoryResponse(
        items=[CategoryResponse(**c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    description="Create a new category with validated input.",
)
async def create_category(
    request: Request,
    payload: CategoryCreate,
    user=Depends(require_permission(Permission.CATEGORY_CREATE)),
) -> CategoryResponse:
    """
    Create a new category.

    Validates that the slug is unique among existing categories.
    Returns the newly created category with 201 status.
    """
    global _next_id

    # Check for duplicate slug
    existing_slugs = {c["slug"] for c in MOCK_CATEGORIES}
    if payload.slug in existing_slugs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with slug '{payload.slug}' already exists.",
        )

    # Validate parent_id if provided
    if payload.parent_id is not None:
        parent_ids = {c["id"] for c in MOCK_CATEGORIES}
        if payload.parent_id not in parent_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent category with id {payload.parent_id} does not exist.",
            )

    now = datetime.utcnow()
    new_category = {
        "id": _next_id,
        "name": payload.name,
        "slug": payload.slug,
        "description": payload.description,
        "parent_id": payload.parent_id,
        "icon": payload.icon,
        "is_active": payload.is_active,
        "sort_order": payload.sort_order,
        "created_at": now,
        "updated_at": now,
        "product_count": 0,
    }

    MOCK_CATEGORIES.append(new_category)
    _next_id += 1

    return CategoryResponse(**new_category)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a category by ID",
    description="Retrieve a single category by its numeric ID.",
)
async def get_category(
    request: Request,
    category_id: int,
    user=Depends(require_permission(Permission.CATEGORY_READ)),
) -> CategoryResponse:
    """
    Return a single category by ID.

    Raises 404 if the category does not exist.
    """
    category = _get_category_or_404(category_id)
    return CategoryResponse(**category)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category",
    description="Update an existing category. Only provided fields are modified.",
)
async def update_category(
    request: Request,
    category_id: int,
    payload: CategoryUpdate,
    user=Depends(require_permission(Permission.CATEGORY_UPDATE)),
) -> CategoryResponse:
    """
    Update an existing category.

    Validates slug uniqueness and parent_id existence when those fields are provided.
    Returns the updated category.
    """
    category = _get_category_or_404(category_id)

    update_data = payload.model_dump(exclude_unset=True)

    # Check for duplicate slug if slug is being changed
    if "slug" in update_data and update_data["slug"] != category["slug"]:
        existing_slugs = {c["slug"] for c in MOCK_CATEGORIES if c["id"] != category_id}
        if update_data["slug"] in existing_slugs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with slug '{update_data['slug']}' already exists.",
            )

    # Validate parent_id if provided
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        parent_ids = {c["id"] for c in MOCK_CATEGORIES if c["id"] != category_id}
        if update_data["parent_id"] not in parent_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent category with id {update_data['parent_id']} does not exist.",
            )

    category.update(update_data)
    category["updated_at"] = datetime.utcnow()

    return CategoryResponse(**category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    description="Delete a category by ID. Returns 204 No Content on success.",
)
async def delete_category(
    request: Request,
    category_id: int,
    user=Depends(require_permission(Permission.CATEGORY_DELETE)),
) -> None:
    """
    Delete a category by ID.

    Raises 404 if the category does not exist.
    """
    category = _get_category_or_404(category_id)
    MOCK_CATEGORIES.remove(category)
