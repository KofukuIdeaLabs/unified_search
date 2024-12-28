from app import crud, schemas
from app.constants.role import Role
from app.core.config import settings
from sqlalchemy.orm import Session
import logging
import os


def init_db(db: Session) -> None:
    logging.info("Creating Initial Data")

    # Create Role If They Don't Exist
    super_admin_role = crud.role.get_by_name(db, name=Role.SUPER_ADMIN["name"])
    if not super_admin_role:
        super_admin_role_in = schemas.RoleCreate(
            name=Role.SUPER_ADMIN["name"],
            description=Role.SUPER_ADMIN["description"],
        )
        super_admin_role = crud.role.create(db, obj_in=super_admin_role_in)

    admin_role = crud.role.get_by_name(db, name=Role.ADMIN["name"])
    if not admin_role:
        admin_role_in = schemas.RoleCreate(
            name=Role.ADMIN["name"], description=Role.ADMIN["description"]
        )
        admin_role = crud.role.create(db, obj_in=admin_role_in)

    member_role = crud.role.get_by_name(db, name=Role.MEMBER["name"])
    if not member_role:
        member_role_in = schemas.RoleCreate(
            name=Role.MEMBER["name"],
            description=Role.MEMBER["description"],
        )
        member_role = crud.role.create(db, obj_in=member_role_in)

    guest_role = crud.role.get_by_name(db, name=Role.GUEST["name"])
    print(guest_role,"this is guest role")
    if not guest_role:
        guest_role_in = schemas.RoleCreate(
            name=Role.GUEST["name"],
            description=Role.GUEST["description"],
        )
        print(guest_role_in,"this is guest role in")
        guest_role = crud.role.create(db, obj_in=guest_role_in)



    # Create 1st Organization
    organization = crud.organization.get_by_name(
        db, name=os.getenv("ORGANIZATION_NAME")
    )
    if not organization:
        organization_in = schemas.OrganizationCreate(
            name=settings.DEFAULT_ORGANIZATION_NAME     ,
            description=settings.DEFAULT_ORGANIZATION_DESCRIPTION,
        )
        organization = crud.organization.create(db, obj_in=organization_in)

    # Create 1st Superuser
    super_admin_user = crud.app_user.get_by_email(db, email=settings.DEFAULT_SUPER_ADMIN_EMAIL)
    if not super_admin_user:
      

        user_in = schemas.AppUserCreate(
            email=settings.DEFAULT_SUPER_ADMIN_EMAIL,
            password=settings.DEFAULT_SUPER_ADMIN_PASSWORD,
            full_name=settings.DEFAULT_SUPER_ADMIN_FULL_NAME,
            is_active=True,
            role_id=super_admin_role.id,
            org_id=organization.id,
        )
        super_admin_user = crud.app_user.create(db, obj_in=user_in)
    
    # Create 1st AdminUser
    admin_user = crud.app_user.get_by_email(db, email=settings.DEFAULT_ADMIN_EMAIL)
    if not admin_user:
        organization = crud.organization.get_by_name(
            db, name=settings.DEFAULT_ORGANIZATION_NAME
        )

        user_in = schemas.AppUserCreate(
            email=settings.DEFAULT_ADMIN_EMAIL,
            password=settings.DEFAULT_ADMIN_PASSWORD,
            full_name=settings.DEFAULT_ADMIN_FULL_NAME,
            role_id=admin_role.id,
            org_id=organization.id,
        )
        admin_user = crud.app_user.create(db, obj_in=user_in)

    # Create 1st memberuser
    member_user = crud.app_user.get_by_email(db, email=settings.DEFAULT_MEMBER_EMAIL)
    if not member_user:
        organization = crud.organization.get_by_name(
            db, name=settings.DEFAULT_ORGANIZATION_NAME
        )

        user_in = schemas.AppUserCreate(
            email=settings.DEFAULT_MEMBER_EMAIL,
            password=settings.DEFAULT_MEMBER_PASSWORD,
            full_name=settings.DEFAULT_MEMBER_FULL_NAME,
            role_id=member_role.id,
            org_id=organization.id,
        )
        member_user = crud.app_user.create(db, obj_in=user_in)
    guest_user = crud.app_user.get_by_email(db, email=settings.DEFAULT_GUEST_EMAIL)
    if not guest_user:
        organization = crud.organization.get_by_name(
            db, name=settings.DEFAULT_ORGANIZATION_NAME
        )

        user_in = schemas.AppUserCreate(
            email=settings.DEFAULT_GUEST_EMAIL,
            password=settings.DEFAULT_GUEST_PASSWORD,
            full_name=settings.DEFAULT_GUEST_FULL_NAME,
            role_id=guest_role.id,
            org_id=organization.id,
        )
        guest_user = crud.app_user.create(db, obj_in=user_in)


  