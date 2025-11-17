-- ============================================
-- MUNIFY DATABASE SCHEMA - PostgreSQL
-- Municipal Funding Platform (Based on BRD v3.0)
-- ============================================

-- Enable text search extension
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search



Create table perdix_mp_organization_types (
    id BIGSERIAL PRIMARY KEY,
    organization_type VARCHAR(255) NOT NULL CHECK (organization_type IN ('municipality', 'lender', 'admin', 'government')),
    organization_type_description TEXT NOT NULL ,
    status VARCHAR(50) NOT NULL CHECK (status IN ('A', 'I')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
   UNIQUE (organization_type)
);

CREATE TABLE perdix_mp_roles_master (
    id BIGSERIAL PRIMARY KEY,
    role_name VARCHAR(255) NOT NULL,
    role_description TEXT NOT NULL ,
    status VARCHAR(50) NOT NULL CHECK (status IN ('A', 'I')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE (role_name)
);


-- Users
CREATE TABLE perdix_mp_users_details (
    id BIGSERIAL primary key,
    organization_name VARCHAR(255) NOT NULL ,
    organization_type VARCHAR(50) NOT NULL ,
    user_id varchar(255) NOT NULL,
    user_role BIGINT NOT NULL ,
    user_name VARCHAR(200),
    user_email VARCHAR(255) NOT NULL,
    user_mobile_number VARCHAR(20),
    designation VARCHAR(100),
    registration_number VARCHAR(100),
    is_t&c_accepted BOOLEAN DEFAULT FALSE,
    state VARCHAR(100),
    district VARCHAR(100),
    gstn_ulb_code VARCHAR(50),
    annual_budget_size DECIMAL(15, 2),
    status VARCHAR(50) ,
    is_mobile_verified BOOLEAN DEFAULT FALSE,
    mobile_verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    file_id BIGINT REFERENCES perdix_mp_files(id),
    UNIQUE (user_id)
);

create table perdix_mp_document_master (
    id BIGSERIAL ,
    organization_type VARCHAR(255) NOT NULL ,
    document_category VARCHAR(255) NOT NULL ,
    document_type VARCHAR(255) NOT NULL ,
    document_name VARCHAR(255) NOT NULL ,
    document_description TEXT NOT NULL ,
    status VARCHAR(50) NOT NULL CHECK (status IN ('A', 'I')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE (organization_type, document_category, document_type)
);

create table perdix_mp_kyc_documents (
    id BIGSERIAL ,
    user_id varchar(255) NOT NULL ,
    document_type VARCHAR(255) NOT NULL ,
    document_url VARCHAR(255) NOT NULL ,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE (user_id, document_type)
);

create table perdix_mp_user_auth_audit_trails (  
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES perdix_mp_users_details(user_id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN ('login', 'logout', 'password_reset', 'email_verification', 'phone_verification')),
    action_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- ============================================
-- AUTHENTICATION & SECURITY
-- ============================================

-- OTP Management
CREATE TABLE perdix_mp_otps (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255),
    mobile_number VARCHAR(20),
    purpose VARCHAR(50) NOT NULL CHECK (purpose IN ('registration', 'login', 'password_reset', 'email_verification', 'phone_verification')),
    resend_count INT DEFAULT 0,
    last_resent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Invitations (Phase 1 - Invitation Only Onboarding)
CREATE TABLE perdix_mp_invites (
    id BIGSERIAL PRIMARY KEY,
    token VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    mobile_number VARCHAR(20) NOT NULL,
    user_id varchar(255) NOT NULL,
    user_name VARCHAR(200) NOT NULL ,
    organization_id varchar(255) NOT NULL ,
    organization_type VARCHAR(50) NOT NULL ,
    role_id varchar(255) NOT NULL ,
    invited_by VARCHAR(255) NOT NULL ,
    status VARCHAR(50) DEFAULT 'P' CHECK (status IN ('P', 'A', 'E', 'R')),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    resend_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE (email, mobile_number, user_id,token)
);

-- Refresh Tokens
CREATE TABLE perdix_mp_access_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL ,
    token_hash VARCHAR(255) NOT NULL ,
    device_info VARCHAR(255) NOT NULL ,
    ip_address VARCHAR(255) NOT NULL ,
    user_agent VARCHAR(255) NOT NULL ,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE (user_id, token_hash)
);


-- ============================================
-- FEE MANAGEMENT (BRD MUNI03)
-- ============================================

-- Fee Configurations (Per Organization)
CREATE TABLE perdix_mp_fee_configurations (
    id BIGSERIAL PRIMARY KEY,
    orgnanisation_type VARCHAR(255) NOT NULL ,
    
    -- Subscription Fee (Annual)
    subscription_fee_annual DECIMAL(10, 2) DEFAULT 0,
    subscription_fee_currency VARCHAR(10) DEFAULT 'INR',
    is_subscription_applicable BOOLEAN DEFAULT TRUE,
    
    -- Listing Fee (% of project funding, on success)
    listing_fee_percentage DECIMAL(5, 2) DEFAULT 0, -- e.g., 2.5%
    listing_fee_fixed DECIMAL(10, 2) DEFAULT 0,
    is_listing_fee_applicable BOOLEAN DEFAULT TRUE,
    is_listing_fee_on_success_only BOOLEAN DEFAULT TRUE,
    
    -- Commitment Fee 
    commitment_fee_percentage DECIMAL(5, 2) DEFAULT 0,
    commitment_fee_fixed DECIMAL(10, 2) DEFAULT 0,
    is_commitment_fee_applicable BOOLEAN DEFAULT FALSE,
    
    -- Success Fee (Exploratory)
    success_fee_percentage DECIMAL(5, 2) DEFAULT 0,
    success_fee_fixed DECIMAL(10, 2) DEFAULT 0,
    is_success_fee_applicable BOOLEAN DEFAULT FALSE,
    
    -- Exemptions
    is_fee_exempt BOOLEAN DEFAULT FALSE, -- For Govt/NIUA invited users
    exemption_reason TEXT,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE (organization_type)
);

-- Fee Transactions (All fee payments)
CREATE TABLE perdix_mp_fee_transactions (
    id BIGSERIAL PRIMARY KEY,
    organization_type VARCHAR(255) NOT NULL ,
    organization_id varchar(255) NOT NULL ,
    project_id varchar(255) NULL ,
    
    -- Transaction Details
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('subscription', 'subscription_renewal', 'listing_fee', 'commitment_fee', 'success_fee')),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    
    -- Payment Method
    payment_method VARCHAR(50) CHECK (payment_method IN ('offline', 'razorpay', 'bank_transfer')),
    payment_mode VARCHAR(50) CHECK (payment_mode IN ('online', 'offline')),
    
    -- Razorpay Integration
    razorpay_payment_id VARCHAR(100),
    razorpay_order_id VARCHAR(100),
    
    -- Offline Payment Details
    offline_reference_number VARCHAR(100),
    offline_payment_date DATE,
    offline_remarks TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded')),
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Invoice
    invoice_number VARCHAR(100) ,
    invoice_url VARCHAR(500),
    
    -- Metadata
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Subscription Renewals Tracking
CREATE TABLE perdix_mp_subscription_renewals (
    id BIGSERIAL PRIMARY KEY,
    organization_id varchar(255) NOT NULL ,
    fee_transaction_id BIGINT REFERENCES perdix_mp_fee_transactions(id),
    
    renewal_period_start DATE NOT NULL,
    renewal_period_end DATE NOT NULL,
    renewal_amount DECIMAL(10, 2) NOT NULL,
    
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'expired', 'cancelled')),
    
    
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- ============================================
-- PROJECTS (BRD MUNI04)
-- ============================================

-- Projects
CREATE TABLE perdix_mp_projects (
    id BIGSERIAL PRIMARY KEY,
    organization_type VARCHAR(255) NOT NULL ,
    organization_id varchar(255) NOT NULL ,
    
    -- Project Identification
    project_reference_id VARCHAR(100) NOT NULL, -- System-generated: PROJ-YYYY-XXXXX
    title VARCHAR(500) NOT NULL,
    department VARCHAR(200),
    contact_person VARCHAR(255) NOT NULL ,
    
    -- Project Overview
    category VARCHAR(100), -- Infrastructure, Sanitation, Water Supply, Transportation, Renewable Energy
    project_stage VARCHAR(50) DEFAULT 'planning' CHECK (project_stage IN ('planning', 'initiated', 'in_progress')),
    description TEXT,
    start_date DATE,
    end_date DATE,
    
    -- Financial Information
    total_project_cost DECIMAL(15, 2),
    funding_requirement DECIMAL(15, 2) NOT NULL,
    already_secured_funds DECIMAL(15, 2) DEFAULT 0,
    commitment_gap DECIMAL(15, 2) GENERATED ALWAYS AS (funding_requirement - already_secured_funds) STORED,
    currency VARCHAR(10) DEFAULT 'INR',
    
    -- Fundraising Timeline
    fundraising_start_date TIMESTAMP WITH TIME ZONE,
    fundraising_end_date TIMESTAMP WITH TIME ZONE, -- Closure date for commitments
    
    
    -- Credit & Rating
    municipality_credit_rating VARCHAR(20),
    municipality_credit_score DECIMAL(5, 2),
    
    -- Status & Workflow
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN (
        'draft', 
        'pending_validation', 
        'active', 
        'funding_completed',
        'closed',
        'rejected'
    )),
    visibility VARCHAR(50) DEFAULT 'private' CHECK (visibility IN ('private', 'public')),
    
    -- Calculated Fields
    funding_raised DECIMAL(15, 2) DEFAULT 0, -- Sum of approved commitments
    funding_percentage DECIMAL(5, 2) GENERATED ALWAYS AS (
        CASE WHEN funding_requirement > 0 
        THEN (funding_raised / funding_requirement * 100) 
        ELSE 0 END
    ) STORED,
    
    -- Source & Audit
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by varchar(255) NOT NULL ,
    admin_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
);

-- Project Documents
CREATE TABLE perdix_mp_project_documents (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL ,
    file_id BIGINT NOT NULL REFERENCES perdix_mp_files(id),
    
    document_type VARCHAR(100) NOT NULL, -- dpr, feasibility_study, compliance_certificate, budget_approval, tender_rfp
    version INT DEFAULT 1,
    access_level VARCHAR(50) DEFAULT 'public' CHECK (access_level IN ('public', 'restricted', 'private')),
    
    uploaded_by varchar(255) NOT NULL ,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Project Progress Updates (BRD MUNI06c)
CREATE TABLE perdix_mp_project_progress_updates (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id),
    
    milestone_title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Project Progress Update Media Files
CREATE TABLE perdix_mp_project_progress_update_media (
    id BIGSERIAL PRIMARY KEY,
    progress_update_id BIGINT NOT NULL REFERENCES perdix_mp_project_progress_updates(id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES perdix_mp_files(id),
    
    media_type VARCHAR(50) NOT NULL CHECK (media_type IN ('photo', 'video', 'document')),
    display_order INT DEFAULT 0, -- For ordering media files
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- ============================================
-- COMMITMENTS (BRD MUNI05b)
-- ============================================

-- Commitments
CREATE TABLE perdix_mp_commitments (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    organization_type VARCHAR(255) NOT NULL ,
    organization_id varchar(255) NOT NULL ,
    committed_by varchar(255) NOT NULL ,
    
    -- Commitment Details
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    funding_mode VARCHAR(50) NOT NULL CHECK (funding_mode IN ('loan', 'grant', 'csr')), -- BRD: Loan / Grant / CSR
    interest_rate DECIMAL(5, 2), -- For loans
    
    -- Terms & Conditions (BRD: 250 words free-text)
    terms_conditions_text TEXT, -- Free text field for lenders
    
    
    -- Status & Workflow
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('draft', 'pending', 'under_review', 'approved', 'rejected', 'withdrawn', 'funded', 'completed')),
    can_modify BOOLEAN DEFAULT TRUE, -- BRD: Can withdraw/modify before funding window closure
    is_locked BOOLEAN DEFAULT FALSE,
    
    -- Approval
    approved_by VARCHAR(255) NOT NULL ,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    rejection_notes TEXT,
    
    -- Acknowledgment (BRD 10.1)
    acknowledgment_receipt_url VARCHAR(500),
    acknowledgment_generated_at TIMESTAMP WITH TIME ZONE,
    
     -- For tracking updates
    update_count INT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);



-- Commitment History (Track all updates)
CREATE TABLE perdix_mp_commitment_history (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_commitments(project_id) ON DELETE CASCADE,
    organization_type VARCHAR(255) NOT NULL ,
    organization_id varchar(255) NOT NULL ,
    committed_by varchar(255) NOT NULL ,
    amount DECIMAL(15, 2),
    funding_mode VARCHAR(50),
    interest_rate DECIMAL(5, 2),
    terms_conditions_text TEXT,
    status VARCHAR(50),
    
    action VARCHAR(50), -- created, updated, withdrawn
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Commitment Documents
CREATE TABLE perdix_mp_commitment_documents (
    id BIGSERIAL PRIMARY KEY,
    commitment_id varchar(255) NOT NULL REFERENCES perdix_mp_commitments(id) ON DELETE CASCADE,
    file_id BIGINT NOT NULL REFERENCES perdix_mp_files(id),
    document_type VARCHAR(100) NOT NULL, -- sanction_letter, approval_note, kyc, terms_sheet, due_diligence
    is_required BOOLEAN DEFAULT TRUE,
    uploaded_by varchar(255) NOT NULL ,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Commitment Comments/Notes
CREATE TABLE perdix_mp_commitment_comments (
    id BIGSERIAL PRIMARY KEY,
    commitment_id varchar(255) NOT NULL REFERENCES perdix_mp_commitments(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL ,
    comment TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE, -- Internal admin notes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- ============================================
-- Q&A SYSTEM (BRD MUNI05e, MUNI06a, MUNI06b)
-- ============================================

-- Questions (Public, visible to all)
CREATE TABLE perdix_mp_questions (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    
    asked_by varchar(255) NOT NULL ,
    question_text TEXT NOT NULL,
    category VARCHAR(100), -- BRD: financial, compliance, timeline, etc.
    attachments JSONB DEFAULT '[]', -- Array of file IDs
    
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('draft', 'open', 'answered', 'closed')),
    is_public BOOLEAN DEFAULT TRUE, -- BRD: All Q&A visible to all users
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Question Replies
CREATE TABLE perdix_mp_question_replies (
    id BIGSERIAL PRIMARY KEY,
    question_id BIGINT NOT NULL REFERENCES perdix_mp_questions(id) ON DELETE CASCADE,
    replied_by_user_id BIGINT NOT NULL REFERENCES perdix_mp_users(id),
    
    reply_text TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    document_links TEXT, -- BRD: Response may provide link to documents
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Q&A Sessions (BRD MUNI06b - Offline Zoom/Teams meetings)
CREATE TABLE perdix_mp_qa_sessions (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    
    -- Session Details
    title VARCHAR(255) NOT NULL,
    agenda TEXT,
    description TEXT,
    
    -- Scheduling (Offline)
    scheduled_date TIMESTAMP WITH TIME ZONE NOT NULL,
    scheduled_time TIME,
    duration_minutes INT DEFAULT 60,
    
    -- Meeting Platform (BRD: Zoom, MS Teams, Google Meet)
    meeting_platform VARCHAR(50) CHECK (meeting_platform IN ('zoom', 'microsoft_teams', 'google_meet', 'other')),
    meeting_link VARCHAR(500),
    
    -- Post-Session (BRD: Recording uploaded)
    session_recording_url VARCHAR(500),
    session_transcript_url VARCHAR(500),
    session_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Notifications
    notified_lenders BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMP WITH TIME ZONE,
    
    -- Organizer
    organized_by varchar(255) NOT NULL ,
    
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);



-- ============================================
-- REQUESTS & SEND-BACKS (BRD MUNI05f, MUNI06a)
-- ============================================

-- Requests (Additional docs/meetings)
CREATE TABLE perdix_mp_requests (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    commitment_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_commitments(id) ON DELETE CASCADE,
    
    requesting_org_id varchar(255) NOT NULL ,
    
    request_type VARCHAR(50) NOT NULL CHECK (request_type IN ('additional_document', 'meeting', 'clarification', 'information')),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    

    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- Send-backs (Lender responses)
CREATE TABLE perdix_mp_send_backs (
    id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL REFERENCES perdix_mp_requests(id) ON DELETE CASCADE,
    sent_by_org_id varchar(255) NOT NULL ,
    sent_by_user_id varchar(255) NOT NULL ,
    
    response_text TEXT,
    documents JSONB DEFAULT '[]', -- Array of file IDs
    
    status VARCHAR(50) DEFAULT 'submitted' CHECK (status IN ('draft', 'submitted', 'reviewed', 'accepted', 'rejected')),
    remarks TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- ============================================
-- DOCUMENT/FILE MANAGEMENT
-- ============================================

-- Files
CREATE TABLE perdix_mp_files (
    id BIGSERIAL PRIMARY KEY,
    organization_id varchar(255) NOT NULL ,
    uploaded_by varchar(255) NOT NULL ,
    
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL, -- bytes
    storage_path VARCHAR(1000) NOT NULL, -- S3/local path
    checksum VARCHAR(64) NOT NULL, -- SHA-256
    
    access_level VARCHAR(50) DEFAULT 'private' CHECK (access_level IN ('public', 'restricted', 'private')),
    
    download_count INT DEFAULT 0,
    
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
);

-- ============================================
-- FAVORITES & NOTES (BRD MUNI05c, MUNI05d)
-- ============================================

-- Project Favorites
CREATE TABLE perdix_mp_project_favorites (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    organization_id varchar(255) NOT NULL ,
    user_id varchar(255) NOT NULL ,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    UNIQUE(project_id, organization_id, user_id)
);

-- Project Notes (BRD: Private to organization, visible to all users within org)
CREATE TABLE perdix_mp_project_notes (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    organization_id varchar(255) NOT NULL ,
    
    title VARCHAR(255),
    content TEXT NOT NULL, -- BRD: 5,000 characters limit
    tags JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    
    CONSTRAINT content_length_check CHECK (LENGTH(content) <= 5000)
);

CREATE TABLE perdix_mp_project_engagements (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(255) NOT NULL REFERENCES perdix_mp_projects(project_reference_id) ON DELETE CASCADE,
    view_count INT DEFAULT 0,
    favorite_count INT DEFAULT 0,
    commitment_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255)
)


-- Organizations
CREATE INDEX idx_perdix_mp_organizations_type ON perdix_mp_organizations(type);
CREATE INDEX idx_perdix_mp_organizations_status ON perdix_mp_organizations(status);
CREATE INDEX idx_perdix_mp_organizations_subscription_status ON perdix_mp_organizations(subscription_status);
CREATE INDEX idx_perdix_mp_organizations_lender_type ON perdix_mp_organizations(lender_type) WHERE type = 'lender';
CREATE INDEX idx_perdix_mp_organizations_is_govt_invited ON perdix_mp_organizations(is_govt_invited) WHERE is_govt_invited = TRUE;
CREATE INDEX idx_perdix_mp_organizations_deleted_at ON perdix_mp_organizations(deleted_at) WHERE deleted_at IS NULL;

-- Users
CREATE INDEX idx_perdix_mp_users_email ON perdix_mp_users(email);
CREATE INDEX idx_perdix_mp_users_user_id ON perdix_mp_users(user_id);
CREATE INDEX idx_perdix_mp_users_organization_id ON perdix_mp_users(organization_id);
CREATE INDEX idx_perdix_mp_users_status ON perdix_mp_users(status);
CREATE INDEX idx_perdix_mp_users_deleted_at ON perdix_mp_users(deleted_at) WHERE deleted_at IS NULL;

-- User Roles
CREATE INDEX idx_perdix_mp_user_roles_user_id ON perdix_mp_user_roles(user_id);
CREATE INDEX idx_perdix_mp_user_roles_role_id ON perdix_mp_user_roles(role_id);

-- OTPs
-- CREATE INDEX idx_perdix_mp_otps_user_id ON perdix_mp_otps(user_id); -- commented out as user_id is commented in table
CREATE INDEX idx_perdix_mp_otps_email ON perdix_mp_otps(email);
-- CREATE INDEX idx_perdix_mp_otps_expires_at ON perdix_mp_otps(expires_at); -- commented out as expires_at is commented in table
CREATE INDEX idx_perdix_mp_otps_purpose ON perdix_mp_otps(purpose);

-- Invites
-- CREATE INDEX idx_perdix_mp_invites_invite_code ON perdix_mp_invites(invite_code); -- commented out as invite_code is commented in table
CREATE INDEX idx_perdix_mp_invites_email ON perdix_mp_invites(email);
CREATE INDEX idx_perdix_mp_invites_organization_id ON perdix_mp_invites(organization_id);
CREATE INDEX idx_perdix_mp_invites_status ON perdix_mp_invites(status);
CREATE INDEX idx_perdix_mp_invites_expires_at ON perdix_mp_invites(expires_at);

-- Refresh Tokens
CREATE INDEX idx_perdix_mp_refresh_tokens_user_id ON perdix_mp_refresh_tokens(user_id);
CREATE INDEX idx_perdix_mp_refresh_tokens_token_hash ON perdix_mp_refresh_tokens(token_hash);
CREATE INDEX idx_perdix_mp_refresh_tokens_expires_at ON perdix_mp_refresh_tokens(expires_at);

-- Fee Configurations
CREATE INDEX idx_perdix_mp_fee_configurations_organization_id ON perdix_mp_fee_configurations(organization_id);
CREATE INDEX idx_perdix_mp_fee_configurations_is_fee_exempt ON perdix_mp_fee_configurations(is_fee_exempt) WHERE is_fee_exempt = TRUE;

-- Fee Transactions
CREATE INDEX idx_perdix_mp_fee_transactions_organization_id ON perdix_mp_fee_transactions(organization_id);
CREATE INDEX idx_perdix_mp_fee_transactions_project_id ON perdix_mp_fee_transactions(project_id);
CREATE INDEX idx_perdix_mp_fee_transactions_transaction_type ON perdix_mp_fee_transactions(transaction_type);
CREATE INDEX idx_perdix_mp_fee_transactions_status ON perdix_mp_fee_transactions(status);
CREATE INDEX idx_perdix_mp_fee_transactions_created_at ON perdix_mp_fee_transactions(created_at DESC);

-- Subscription Renewals
CREATE INDEX idx_perdix_mp_subscription_renewals_organization_id ON perdix_mp_subscription_renewals(organization_id);
CREATE INDEX idx_perdix_mp_subscription_renewals_status ON perdix_mp_subscription_renewals(status);
CREATE INDEX idx_perdix_mp_subscription_renewals_period_end ON perdix_mp_subscription_renewals(renewal_period_end);

-- Projects
CREATE INDEX idx_perdix_mp_projects_organization_id ON perdix_mp_projects(organization_id);
CREATE INDEX idx_perdix_mp_projects_project_reference_id ON perdix_mp_projects(project_reference_id);
CREATE INDEX idx_perdix_mp_projects_status ON perdix_mp_projects(status);
CREATE INDEX idx_perdix_mp_projects_visibility ON perdix_mp_projects(visibility);
CREATE INDEX idx_perdix_mp_projects_slug ON perdix_mp_projects(slug);
CREATE INDEX idx_perdix_mp_projects_category ON perdix_mp_projects(category);
CREATE INDEX idx_perdix_mp_projects_project_stage ON perdix_mp_projects(project_stage);
CREATE INDEX idx_perdix_mp_projects_fundraising_end_date ON perdix_mp_projects(fundraising_end_date);
CREATE INDEX idx_perdix_mp_projects_featured ON perdix_mp_projects(featured) WHERE featured = TRUE;
CREATE INDEX idx_perdix_mp_projects_deleted_at ON perdix_mp_projects(deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX idx_perdix_mp_projects_created_at ON perdix_mp_projects(created_at DESC);
CREATE INDEX idx_perdix_mp_projects_location_coordinates ON perdix_mp_projects USING GIST(location_coordinates);
CREATE INDEX idx_perdix_mp_projects_sdg_tags ON perdix_mp_projects USING GIN(sdg_tags);
CREATE INDEX idx_perdix_mp_projects_title_trgm ON perdix_mp_projects USING GIN(title gin_trgm_ops);
CREATE INDEX idx_perdix_mp_projects_description_trgm ON perdix_mp_projects USING GIN(description gin_trgm_ops);
CREATE INDEX idx_perdix_mp_projects_active_marketplace ON perdix_mp_projects(status, visibility) WHERE status = 'active' AND deleted_at IS NULL;

-- Project Documents
CREATE INDEX idx_perdix_mp_project_documents_project_id ON perdix_mp_project_documents(project_id);
CREATE INDEX idx_perdix_mp_project_documents_file_id ON perdix_mp_project_documents(file_id);
CREATE INDEX idx_perdix_mp_project_documents_document_type ON perdix_mp_project_documents(document_type);

-- Project Progress Updates
CREATE INDEX idx_perdix_mp_project_progress_updates_project_id ON perdix_mp_project_progress_updates(project_id);
CREATE INDEX idx_perdix_mp_project_progress_updates_created_at ON perdix_mp_project_progress_updates(created_at DESC);

-- Project Progress Update Media
CREATE INDEX idx_perdix_mp_project_progress_update_media_progress_update_id ON perdix_mp_project_progress_update_media(progress_update_id);
CREATE INDEX idx_perdix_mp_project_progress_update_media_file_id ON perdix_mp_project_progress_update_media(file_id);
CREATE INDEX idx_perdix_mp_project_progress_update_media_media_type ON perdix_mp_project_progress_update_media(media_type);
CREATE INDEX idx_perdix_mp_project_progress_update_media_display_order ON perdix_mp_project_progress_update_media(progress_update_id, display_order);

-- Commitments
CREATE INDEX idx_perdix_mp_commitments_project_id ON perdix_mp_commitments(project_id);
CREATE INDEX idx_perdix_mp_commitments_lender_org_id ON perdix_mp_commitments(lender_org_id);
CREATE INDEX idx_perdix_mp_commitments_committed_by ON perdix_mp_commitments(committed_by);
CREATE INDEX idx_perdix_mp_commitments_status ON perdix_mp_commitments(status);
CREATE INDEX idx_perdix_mp_commitments_funding_mode ON perdix_mp_commitments(funding_mode);
CREATE INDEX idx_perdix_mp_commitments_can_modify ON perdix_mp_commitments(can_modify) WHERE can_modify = TRUE;
CREATE INDEX idx_perdix_mp_commitments_created_at ON perdix_mp_commitments(created_at DESC);

-- Commitment History
CREATE INDEX idx_perdix_mp_commitment_history_commitment_id ON perdix_mp_commitment_history(commitment_id);
CREATE INDEX idx_perdix_mp_commitment_history_action_at ON perdix_mp_commitment_history(action_at DESC);

-- Commitment Documents
CREATE INDEX idx_perdix_mp_commitment_documents_commitment_id ON perdix_mp_commitment_documents(commitment_id);
CREATE INDEX idx_perdix_mp_commitment_documents_file_id ON perdix_mp_commitment_documents(file_id);

-- Commitment Comments
CREATE INDEX idx_perdix_mp_commitment_comments_commitment_id ON perdix_mp_commitment_comments(commitment_id);
CREATE INDEX idx_perdix_mp_commitment_comments_user_id ON perdix_mp_commitment_comments(user_id);

-- Questions
CREATE INDEX idx_perdix_mp_questions_project_id ON perdix_mp_questions(project_id);
CREATE INDEX idx_perdix_mp_questions_asked_by_org_id ON perdix_mp_questions(asked_by_org_id);
CREATE INDEX idx_perdix_mp_questions_status ON perdix_mp_questions(status);
CREATE INDEX idx_perdix_mp_questions_category ON perdix_mp_questions(category);
CREATE INDEX idx_perdix_mp_questions_created_at ON perdix_mp_questions(created_at DESC);
CREATE INDEX idx_perdix_mp_questions_sla_due_at ON perdix_mp_questions(sla_due_at) WHERE status = 'open';
CREATE INDEX idx_perdix_mp_questions_sla_breached ON perdix_mp_questions(sla_breached) WHERE sla_breached = TRUE;

-- Question Replies
CREATE INDEX idx_perdix_mp_question_replies_question_id ON perdix_mp_question_replies(question_id);
CREATE INDEX idx_perdix_mp_question_replies_replied_by_user_id ON perdix_mp_question_replies(replied_by_user_id);
CREATE INDEX idx_perdix_mp_question_replies_is_draft ON perdix_mp_question_replies(is_draft) WHERE is_draft = TRUE;

-- Q&A Sessions
CREATE INDEX idx_perdix_mp_qa_sessions_project_id ON perdix_mp_qa_sessions(project_id);
CREATE INDEX idx_perdix_mp_qa_sessions_scheduled_date ON perdix_mp_qa_sessions(scheduled_date);
CREATE INDEX idx_perdix_mp_qa_sessions_status ON perdix_mp_qa_sessions(status);
CREATE INDEX idx_perdix_mp_qa_sessions_organized_by ON perdix_mp_qa_sessions(organized_by);

-- Q&A Session Attendees
CREATE INDEX idx_perdix_mp_qa_session_attendees_qa_session_id ON perdix_mp_qa_session_attendees(qa_session_id);
CREATE INDEX idx_perdix_mp_qa_session_attendees_user_id ON perdix_mp_qa_session_attendees(user_id);

-- Requests
CREATE INDEX idx_perdix_mp_requests_project_id ON perdix_mp_requests(project_id);
CREATE INDEX idx_perdix_mp_requests_commitment_id ON perdix_mp_requests(commitment_id);
CREATE INDEX idx_perdix_mp_requests_requesting_org_id ON perdix_mp_requests(requesting_org_id);
CREATE INDEX idx_perdix_mp_requests_target_org_id ON perdix_mp_requests(target_org_id);
CREATE INDEX idx_perdix_mp_requests_status ON perdix_mp_requests(status);
CREATE INDEX idx_perdix_mp_requests_due_date ON perdix_mp_requests(due_date);

-- Send Backs
CREATE INDEX idx_perdix_mp_send_backs_request_id ON perdix_mp_send_backs(request_id);
CREATE INDEX idx_perdix_mp_send_backs_sent_by_org_id ON perdix_mp_send_backs(sent_by_org_id);
CREATE INDEX idx_perdix_mp_send_backs_status ON perdix_mp_send_backs(status);

-- Files
CREATE INDEX idx_perdix_mp_files_organization_id ON perdix_mp_files(organization_id);
CREATE INDEX idx_perdix_mp_files_uploaded_by ON perdix_mp_files(uploaded_by);
CREATE INDEX idx_perdix_mp_files_av_scan_status ON perdix_mp_files(av_scan_status);
CREATE INDEX idx_perdix_mp_files_created_at ON perdix_mp_files(created_at DESC);
CREATE INDEX idx_perdix_mp_files_is_deleted ON perdix_mp_files(is_deleted) WHERE is_deleted = FALSE;

-- Project Favorites
CREATE INDEX idx_perdix_mp_project_favorites_project_id ON perdix_mp_project_favorites(project_id);
CREATE INDEX idx_perdix_mp_project_favorites_organization_id ON perdix_mp_project_favorites(organization_id);
CREATE INDEX idx_perdix_mp_project_favorites_user_id ON perdix_mp_project_favorites(user_id);

-- Project Notes
CREATE INDEX idx_perdix_mp_project_notes_project_id ON perdix_mp_project_notes(project_id);
CREATE INDEX idx_perdix_mp_project_notes_organization_id ON perdix_mp_project_notes(organization_id);
CREATE INDEX idx_perdix_mp_project_notes_created_by ON perdix_mp_project_notes(created_by);

-- Notifications
CREATE INDEX idx_perdix_mp_notifications_user_id ON perdix_mp_notifications(user_id);
CREATE INDEX idx_perdix_mp_notifications_organization_id ON perdix_mp_notifications(organization_id);
CREATE INDEX idx_perdix_mp_notifications_project_id ON perdix_mp_notifications(project_id);
CREATE INDEX idx_perdix_mp_notifications_is_read ON perdix_mp_notifications(is_read);
CREATE INDEX idx_perdix_mp_notifications_created_at ON perdix_mp_notifications(created_at DESC);
CREATE INDEX idx_perdix_mp_notifications_type ON perdix_mp_notifications(type);
CREATE INDEX idx_perdix_mp_notifications_delivery_status ON perdix_mp_notifications(delivery_status);

-- Project Closure Reminders
CREATE INDEX idx_perdix_mp_project_closure_reminders_project_id ON perdix_mp_project_closure_reminders(project_id);

-- Audit Events
CREATE INDEX idx_perdix_mp_audit_events_user_id ON perdix_mp_audit_events(user_id);
CREATE INDEX idx_perdix_mp_audit_events_organization_id ON perdix_mp_audit_events(organization_id);
CREATE INDEX idx_perdix_mp_audit_events_event_type ON perdix_mp_audit_events(event_type);
CREATE INDEX idx_perdix_mp_audit_events_entity_type_id ON perdix_mp_audit_events(entity_type, entity_id);
CREATE INDEX idx_perdix_mp_audit_events_created_at ON perdix_mp_audit_events(created_at DESC);

-- User Sessions
CREATE INDEX idx_perdix_mp_user_sessions_user_id ON perdix_mp_user_sessions(user_id);
CREATE INDEX idx_perdix_mp_user_sessions_session_token ON perdix_mp_user_sessions(session_token);
CREATE INDEX idx_perdix_mp_user_sessions_is_active ON perdix_mp_user_sessions(is_active);

-- Search History
CREATE INDEX idx_perdix_mp_search_history_user_id ON perdix_mp_search_history(user_id);
CREATE INDEX idx_perdix_mp_search_history_created_at ON perdix_mp_search_history(created_at DESC);

-- ============================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================

CREATE OR REPLACE FUNCTION perdix_mp_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON perdix_mp_organizations FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON perdix_mp_users FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON perdix_mp_roles FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_invites_updated_at BEFORE UPDATE ON perdix_mp_invites FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_fee_configurations_updated_at BEFORE UPDATE ON perdix_mp_fee_configurations FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_fee_transactions_updated_at BEFORE UPDATE ON perdix_mp_fee_transactions FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON perdix_mp_projects FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_commitments_updated_at BEFORE UPDATE ON perdix_mp_commitments FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_questions_updated_at BEFORE UPDATE ON perdix_mp_questions FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_requests_updated_at BEFORE UPDATE ON perdix_mp_requests FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_project_progress_updates_updated_at BEFORE UPDATE ON perdix_mp_project_progress_updates FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();
CREATE TRIGGER update_project_progress_update_media_updated_at BEFORE UPDATE ON perdix_mp_project_progress_update_media FOR EACH ROW EXECUTE FUNCTION perdix_mp_update_updated_at_column();

-- ============================================
-- TRIGGER: Update project funding_raised when commitment approved
-- ============================================

CREATE OR REPLACE FUNCTION perdix_mp_update_project_funding()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'approved' AND (OLD.status IS NULL OR OLD.status != 'approved') THEN
        UPDATE perdix_mp_projects 
        SET funding_raised = (
            SELECT COALESCE(SUM(amount), 0) 
            FROM perdix_mp_commitments 
            WHERE project_id = NEW.project_id AND status = 'approved'
        ),
        commitment_count = (
            SELECT COUNT(*) 
            FROM perdix_mp_commitments 
            WHERE project_id = NEW.project_id AND status = 'approved'
        )
        WHERE id = NEW.project_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_perdix_mp_update_project_funding
AFTER INSERT OR UPDATE ON perdix_mp_commitments
FOR EACH ROW
EXECUTE FUNCTION perdix_mp_update_project_funding();

-- ============================================
-- TRIGGER: Update project favorite_count
-- ============================================

CREATE OR REPLACE FUNCTION perdix_mp_update_favorite_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE perdix_mp_projects 
        SET favorite_count = favorite_count + 1 
        WHERE id = NEW.project_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE perdix_mp_projects 
        SET favorite_count = GREATEST(favorite_count - 1, 0) 
        WHERE id = OLD.project_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_perdix_mp_update_favorite_count
AFTER INSERT OR DELETE ON perdix_mp_project_favorites
FOR EACH ROW
EXECUTE FUNCTION perdix_mp_update_favorite_count();

-- ============================================
-- TRIGGER: Generate project reference ID
-- ============================================

CREATE OR REPLACE FUNCTION perdix_mp_generate_project_reference_id()
RETURNS TRIGGER AS $$
DECLARE
    year_part VARCHAR(4);
    sequence_part VARCHAR(5);
BEGIN
    IF NEW.project_reference_id IS NULL OR NEW.project_reference_id = '' THEN
        year_part := TO_CHAR(CURRENT_TIMESTAMP, 'YYYY');
        SELECT LPAD((COUNT(*) + 1)::TEXT, 5, '0') INTO sequence_part
        FROM perdix_mp_projects
        WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_TIMESTAMP);
        
        NEW.project_reference_id := 'PROJ-' || year_part || '-' || sequence_part;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_perdix_mp_generate_project_reference_id
BEFORE INSERT ON perdix_mp_projects
FOR EACH ROW
EXECUTE FUNCTION perdix_mp_generate_project_reference_id();

-- ============================================
-- TRIGGER: Track SLA breach for questions
-- ============================================

CREATE OR REPLACE FUNCTION perdix_mp_check_question_sla()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.sla_due_at IS NOT NULL AND NEW.sla_due_at < NOW() AND NEW.status = 'open' THEN
        NEW.sla_breached := TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_perdix_mp_check_question_sla
BEFORE UPDATE ON questions
FOR EACH ROW
EXECUTE FUNCTION perdix_mp_check_question_sla();

-- ============================================
-- COMMENTS ON TABLES
-- ============================================

COMMENT ON TABLE perdix_mp_organizations IS 'Organizations: municipalities, lenders, admin, govt/NIUA bodies';
COMMENT ON TABLE perdix_mp_users IS 'User accounts with authentication credentials and profile information';
COMMENT ON TABLE perdix_mp_roles IS 'RBAC roles with permission sets';
COMMENT ON TABLE perdix_mp_otps IS 'One-time passwords for verification flows (expires in 5 minutes)';
COMMENT ON TABLE perdix_mp_invites IS 'Invitation tokens for user onboarding (Phase 1: invitation-only)';
COMMENT ON TABLE perdix_mp_fee_configurations IS 'Fee structure per organization (subscription, listing, commitment, success fees)';
COMMENT ON TABLE perdix_mp_fee_transactions IS 'All fee payment transactions (online via Razorpay or offline)';
COMMENT ON TABLE perdix_mp_subscription_renewals IS 'Subscription renewal tracking with reminder flags (T-30, T-7, T-1 days)';
COMMENT ON TABLE perdix_mp_projects IS 'Municipal infrastructure projects seeking funding';
COMMENT ON TABLE perdix_mp_commitments IS 'Lender funding commitments to projects (Loan/Grant/CSR)';
COMMENT ON TABLE perdix_mp_commitment_history IS 'Track all commitment updates and withdrawals';
COMMENT ON TABLE perdix_mp_questions IS 'Q&A system for lender-municipality communication (public, visible to all)';
COMMENT ON TABLE perdix_mp_qa_sessions IS 'Offline Q&A sessions (Zoom/Teams) with recordings';
COMMENT ON TABLE perdix_mp_requests IS 'Municipality/Lender requests for documents or meetings';
COMMENT ON TABLE perdix_mp_send_backs IS 'Responses to requests with documents/meeting recordings';
COMMENT ON TABLE perdix_mp_files IS 'File storage metadata with AV scanning and access controls';
COMMENT ON TABLE perdix_mp_project_favorites IS 'Lender bookmarks of projects';
COMMENT ON TABLE perdix_mp_project_notes IS 'Private organization notes (visible to all users within org)';
COMMENT ON TABLE perdix_mp_notifications IS 'In-app notification system with multi-channel support and delivery tracking';
COMMENT ON TABLE perdix_mp_project_closure_reminders IS 'Track closure reminder notifications (T-7, T-1, T=0)';
COMMENT ON TABLE perdix_mp_audit_events IS 'Comprehensive audit log for compliance (who, what, when, before/after values)';
COMMENT ON TABLE perdix_mp_catalogs IS 'Controlled vocabularies for categories, lender types, funding modes, etc.';
COMMENT ON TABLE perdix_mp_sla_policies IS 'SLA policies (BRD: 7 days for Q&A response)';
