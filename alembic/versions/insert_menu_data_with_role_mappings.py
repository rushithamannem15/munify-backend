"""insert_menu_data_with_role_mappings

Revision ID: insert_menu_data
Revises: 
Create Date: 2026-01-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'insert_menu_data'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Role ID mappings (from Perdix system)
ROLE_IDS = {
    'ADMIN': 145,           # Admin role
    'NORMAL_USER': 146,     # Normal User role
    'SUPER_ADMIN': 147,     # Super Admin role
    'GOVERNMENT_USER': 148  # Government User role
}


def upgrade() -> None:
    """Insert menu master, submenu master, and role-org-submenu mapping data."""
    connection = op.get_bind()
    
    # ==================== Step 0: Update CHECK Constraint for org_type ====================
    # Update the constraint to include 'munify' instead of 'admin'
    # First drop the old constraint, then add the new one
    op.execute("""
        ALTER TABLE perdix_mp_role_org_submenu_mapping 
        DROP CONSTRAINT IF EXISTS check_org_type;
    """)
    op.execute("""
        ALTER TABLE perdix_mp_role_org_submenu_mapping 
        ADD CONSTRAINT check_org_type 
        CHECK (org_type IN ('municipality', 'lender', 'munify', 'government'));
    """)
    
    # Helper function to get menu ID by name
    def get_menu_id(menu_name: str) -> int:
        result = connection.execute(
            text("SELECT id FROM perdix_mp_menu_master WHERE menu_name = :name"),
            {"name": menu_name}
        ).scalar()
        if not result:
            raise ValueError(f"Menu '{menu_name}' not found. Make sure menus are inserted first.")
        return result
    
    # Helper function to insert mapping using submenu name
    def insert_mapping(role_id: int, org_type: str, submenu_name: str):
        connection.execute(
            text("""
                INSERT INTO perdix_mp_role_org_submenu_mapping (role_id, org_type, submenu_id, status)
                SELECT :role_id, :org_type, id, 'A'
                FROM perdix_mp_submenu_master
                WHERE submenu_name = :submenu_name
                AND status = 'A'
                ON CONFLICT (role_id, org_type, submenu_id) DO NOTHING
            """),
            {"role_id": role_id, "org_type": org_type, "submenu_name": submenu_name}
        )
    
    # ==================== Step 1: Insert Menu Master Data ====================
    op.execute("""
        INSERT INTO perdix_mp_menu_master (menu_name, menu_icon, description, display_order, status) VALUES
        ('Dashboard', 'dashboard', 'Main dashboard menu', 1, 'A'),
        ('Projects', 'projects', 'Projects management menu', 2, 'A'),
        ('Municipalities', 'municipalities', 'Municipalities management menu', 3, 'A'),
        ('Lender', 'lender', 'Lender features menu', 4, 'A'),
        ('Reports', 'reports', 'Reports menu', 5, 'A'),
        ('Admin', 'admin', 'Admin management menu', 6, 'A'),
        ('Trackings', 'trackings', 'Monitoring and tracking menu', 7, 'A'),
        ('Master', 'master', 'Master data management menu', 8, 'A'),
        ('Components', 'components', 'Component showcase (dev)', 9, 'A')
        ON CONFLICT (menu_name) DO NOTHING;
    """)
    
    # Get menu IDs dynamically
    dashboard_menu_id = get_menu_id('Dashboard')
    projects_menu_id = get_menu_id('Projects')
    municipalities_menu_id = get_menu_id('Municipalities')
    lender_menu_id = get_menu_id('Lender')
    reports_menu_id = get_menu_id('Reports')
    admin_menu_id = get_menu_id('Admin')
    trackings_menu_id = get_menu_id('Trackings')
    master_menu_id = get_menu_id('Master')
    components_menu_id = get_menu_id('Components')
    
    # ==================== Step 2: Insert Submenu Master Data ====================
    
    # Dashboard Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Overview', 'overview', '/main', :menu_id, 1, 'A'),
        ('Municipality Dashboard', 'municipality', '/main/dashboard/municipality', :menu_id, 2, 'A'),
        ('Master Dashboard', 'monitoring', '/main/admin/monitoring', :menu_id, 3, 'A'),
        ('Lender Dashboard', 'lender', '/main/lender/dashboard', :menu_id, 4, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": dashboard_menu_id})
    
    # Projects Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Live Projects', 'live', '/main/projects/live', :menu_id, 1, 'A'),
        ('Funded Projects', 'funded', '/main/projects/funded', :menu_id, 2, 'A'),
        ('My Projects', 'my-projects', '/main/projects/my', :menu_id, 3, 'A'),
        ('Favorites', 'favorites', '/main/projects/favorites', :menu_id, 4, 'A'),
        ('Card Designs', 'card', '/main/designs/cards', :menu_id, 5, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": projects_menu_id})
    
    # Municipalities Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('All Municipalities', 'municipalities', '/main/municipalities', :menu_id, 1, 'A'),
        ('Credit Ratings', 'ratings', '/main/municipal/ratings', :menu_id, 2, 'A'),
        ('Financial Analysis', 'analysis', '/main/municipal/analysis', :menu_id, 3, 'A'),
        ('Q&A Management', 'qa', '/main/municipal/qa', :menu_id, 4, 'A'),
        ('Project Progress', 'progress', '/main/municipal/projects/progress', :menu_id, 5, 'A'),
        ('Documents and Meetings', 'documents', '/main/municipal/document-requests', :menu_id, 6, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": municipalities_menu_id})
    
    # Lender Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Request Documents and Meetings', 'request-documents', '/main/lender/requested-documents', :menu_id, 1, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": lender_menu_id})
    
    # Reports Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Lender Report', 'lender-report', '/main/reports/lender-report', :menu_id, 1, 'A'),
        ('Project-level Commitment Report', 'commitment-report', '/main/reports/project-level-commitment', :menu_id, 2, 'A'),
        ('Project Success Report', 'success-report', '/main/reports/project-success', :menu_id, 3, 'A'),
        ('Current Status Report', 'status-report', '/main/reports/current-status', :menu_id, 4, 'A'),
        ('Project-level Commitment Report (Admin)', 'commitment-admin', '/main/reports/project-level-commitment-admin', :menu_id, 5, 'A'),
        ('Project Success Report (Admin)', 'success-admin', '/main/reports/project-success-admin', :menu_id, 6, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": reports_menu_id})
    
    # Admin Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Project Management', 'project-management', '/main/admin/projects', :menu_id, 1, 'A'),
        ('Create Project', 'create-project', '/main/admin/projects/create', :menu_id, 2, 'A'),
        ('My Drafts', 'drafts', '/main/admin/projects/drafts', :menu_id, 3, 'A'),
        ('User Management', 'users', '/main/admin/users', :menu_id, 4, 'A'),
        ('Invitations Management', 'invitations', '/main/admin/invitations', :menu_id, 5, 'A'),
        ('Send Invitation', 'send-invitation', '/main/admin/invitation', :menu_id, 6, 'A'),
        ('Notifications', 'notifications', '/main/admin/notifications', :menu_id, 7, 'A'),
        ('Commitments Overview', 'commitments', '/main/admin/commitments', :menu_id, 8, 'A'),
        ('Reports', 'reports', '/main/admin/reports', :menu_id, 9, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": admin_menu_id})
    
    # Trackings Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Project Lifecycle Tracker', 'lifecycle', '/main/admin/monitoring/lifecycle', :menu_id, 1, 'A'),
        ('Commitment Monitoring', 'commitment-monitoring', '/main/admin/monitoring/commitments', :menu_id, 2, 'A'),
        ('Q&A & Communication', 'qa-communication', '/main/admin/monitoring/qa', :menu_id, 3, 'A'),
        ('Document Requests & Library', 'document-library', '/main/admin/monitoring/documents', :menu_id, 4, 'A'),
        ('Allocation & Disbursement', 'allocation', '/main/admin/monitoring/allocation-disbursement', :menu_id, 5, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": trackings_menu_id})
    
    # Master Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Roles Management', 'roles', '/main/master/roles', :menu_id, 1, 'A'),
        ('Organizations Management', 'organizations', '/main/master/organizations', :menu_id, 2, 'A'),
        ('Fee Category Exemptions', 'fee-exemptions', '/main/master/fee-category-exemptions', :menu_id, 3, 'A'),
        ('Common Master Excel', 'excel', '/main/master/common-excel', :menu_id, 4, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": master_menu_id})
    
    # Components Submenus
    connection.execute(text("""
        INSERT INTO perdix_mp_submenu_master (submenu_name, submenu_icon, route, menu_id, display_order, status) VALUES
        ('Data Table', 'table', '/main/components/datatable', :menu_id, 1, 'A')
        ON CONFLICT (submenu_name) DO NOTHING;
    """), {"menu_id": components_menu_id})
    
    # ==================== Step 3: Insert Role-Org-Submenu Mappings ====================
    # Using submenu names to get IDs dynamically
    
    # 3.1 Lender Admin Mappings (role_id=145, org_type='lender')
    lender_admin_submenus = [
        'Overview', 'Lender Dashboard', 'Live Projects', 'Funded Projects', 'Favorites',
        'Card Designs', 'All Municipalities', 'Request Documents and Meetings',
        'Lender Report', 'Project-level Commitment Report', 'Project Success Report',
        'Current Status Report', 'User Management', 'Invitations Management',
        'Send Invitation', 'Reports'
    ]
    for submenu in lender_admin_submenus:
        insert_mapping(ROLE_IDS['ADMIN'], 'lender', submenu)
    
    # 3.2 Lender Normal User Mappings (role_id=146, org_type='lender')
    lender_normal_submenus = [
        'Overview', 'Lender Dashboard', 'Live Projects', 'Funded Projects', 'Favorites',
        'All Municipalities', 'Request Documents and Meetings', 'Lender Report',
        'Project-level Commitment Report', 'Project Success Report',
        'Current Status Report', 'Reports'
    ]
    for submenu in lender_normal_submenus:
        insert_mapping(ROLE_IDS['NORMAL_USER'], 'lender', submenu)
    
    # 3.3 Municipality Admin Mappings (role_id=145, org_type='municipality')
    municipality_admin_submenus = [
        'Overview', 'Municipality Dashboard', 'My Projects', 'Create Project', 'My Drafts',
        'All Municipalities', 'Q&A Management', 'Project Progress', 'Documents and Meetings',
        'User Management', 'Invitations Management', 'Send Invitation', 'Reports',
        'Project-level Commitment Report', 'Project Success Report', 'Current Status Report'
    ]
    for submenu in municipality_admin_submenus:
        insert_mapping(ROLE_IDS['ADMIN'], 'municipality', submenu)
    
    # 3.4 Municipality Normal User Mappings (role_id=146, org_type='municipality')
    municipality_normal_submenus = [
        'Overview', 'Municipality Dashboard', 'My Projects', 'All Municipalities',
        'Q&A Management', 'Project Progress', 'Documents and Meetings', 'Reports',
        'Project-level Commitment Report', 'Project Success Report', 'Current Status Report'
    ]
    for submenu in municipality_normal_submenus:
        insert_mapping(ROLE_IDS['NORMAL_USER'], 'municipality', submenu)
    
    # 3.5 Munify Admin Mappings (role_id=145, org_type='munify')
    # All menus except Master menu which is Super Admin only
    connection.execute(text("""
        INSERT INTO perdix_mp_role_org_submenu_mapping (role_id, org_type, submenu_id, status)
        SELECT :role_id, 'munify', id, 'A'
        FROM perdix_mp_submenu_master
        WHERE menu_id != :master_menu_id  -- Exclude Master menu
        AND status = 'A'
        ON CONFLICT (role_id, org_type, submenu_id) DO NOTHING;
    """), {"role_id": ROLE_IDS['ADMIN'], "master_menu_id": master_menu_id})
    
    # 3.6 Munify Normal User Mappings (role_id=146, org_type='munify')
    munify_normal_submenus = [
        'Overview', 'Municipality Dashboard', 'Master Dashboard', 'Lender Dashboard',
        'Live Projects', 'Funded Projects', 'My Projects', 'All Municipalities',
        'Credit Ratings', 'Financial Analysis', 'Q&A Management', 'Project Progress',
        'Lender Report', 'Project-level Commitment Report', 'Project Success Report',
        'Current Status Report', 'Project-level Commitment Report (Admin)',
        'Project Success Report (Admin)', 'Commitments Overview', 'Reports',
        'Project Lifecycle Tracker', 'Commitment Monitoring', 'Q&A & Communication',
        'Document Requests & Library', 'Allocation & Disbursement'
    ]
    for submenu in munify_normal_submenus:
        insert_mapping(ROLE_IDS['NORMAL_USER'], 'munify', submenu)
    
    # 3.7 System Super Admin Mappings (role_id=147, org_type='munify')
    # Full access to ALL menus including Master
    connection.execute(text("""
        INSERT INTO perdix_mp_role_org_submenu_mapping (role_id, org_type, submenu_id, status)
        SELECT :role_id, 'munify', id, 'A'
        FROM perdix_mp_submenu_master
        WHERE status = 'A'
        ON CONFLICT (role_id, org_type, submenu_id) DO NOTHING;
    """), {"role_id": ROLE_IDS['SUPER_ADMIN']})
    
    # 3.8 Government/NIUA User Mappings (role_id=148, org_type='government')
    government_submenus = [
        'Overview', 'Municipality Dashboard', 'Master Dashboard', 'Lender Dashboard',
        'Live Projects', 'Funded Projects', 'Lender Report',
        'Project-level Commitment Report', 'Project Success Report', 'Current Status Report',
        'Project-level Commitment Report (Admin)', 'Project Success Report (Admin)', 'Reports'
    ]
    for submenu in government_submenus:
        insert_mapping(ROLE_IDS['GOVERNMENT_USER'], 'government', submenu)


def downgrade() -> None:
    """Remove all menu data."""
    # Delete mappings first (due to foreign key constraints)
    op.execute("DELETE FROM perdix_mp_role_org_submenu_mapping;")
    
    # Delete submenus
    op.execute("DELETE FROM perdix_mp_submenu_master;")
    
    # Delete menus
    op.execute("DELETE FROM perdix_mp_menu_master;")
