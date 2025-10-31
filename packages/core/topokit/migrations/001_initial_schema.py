"""Initial database schema migration for TopoKit."""

from datetime import datetime, timezone
from ..core.database import Migration

# Migration metadata
VERSION = "001"
NAME = "initial_schema"
DESCRIPTION = "Create initial database schema for TopoKit"

# SQL for creating tables
UP_SQL = """
-- Create topology packs table
CREATE TABLE IF NOT EXISTS topology_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    pack_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create execution traces table
CREATE TABLE IF NOT EXISTS execution_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    topology_pack_id UUID NOT NULL REFERENCES topology_packs(id),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create node executions table
CREATE TABLE IF NOT EXISTS node_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES execution_traces(id),
    node_id VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    confidence_score FLOAT,
    guardrail_results JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create context store table
CREATE TABLE IF NOT EXISTS context_store (
    session_id VARCHAR(255) PRIMARY KEY,
    data JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(255),
    metadata JSONB
);

-- Create audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_topology_packs_name ON topology_packs(name);
CREATE INDEX IF NOT EXISTS idx_topology_packs_created_at ON topology_packs(created_at);
CREATE INDEX IF NOT EXISTS idx_execution_traces_session_id ON execution_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_execution_traces_start_time ON execution_traces(start_time);
CREATE INDEX IF NOT EXISTS idx_node_executions_trace_id ON node_executions(trace_id);
CREATE INDEX IF NOT EXISTS idx_node_executions_node_id ON node_executions(node_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_session_id ON audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for topology_packs
CREATE TRIGGER update_topology_packs_updated_at 
    BEFORE UPDATE ON topology_packs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""

DOWN_SQL = """
-- Drop triggers
DROP TRIGGER IF EXISTS update_topology_packs_updated_at ON topology_packs;

-- Drop function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop indexes
DROP INDEX IF EXISTS idx_audit_logs_created_at;
DROP INDEX IF EXISTS idx_audit_logs_session_id;
DROP INDEX IF EXISTS idx_node_executions_node_id;
DROP INDEX IF EXISTS idx_node_executions_trace_id;
DROP INDEX IF EXISTS idx_execution_traces_start_time;
DROP INDEX IF EXISTS idx_execution_traces_session_id;
DROP INDEX IF EXISTS idx_topology_packs_created_at;
DROP INDEX IF EXISTS idx_topology_packs_name;

-- Drop tables
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS context_store;
DROP TABLE IF EXISTS node_executions;
DROP TABLE IF EXISTS execution_traces;
DROP TABLE IF EXISTS topology_packs;
"""

# Create migration object
migration = Migration(
    version=VERSION,
    name=NAME,
    description=DESCRIPTION,
    up_sql=UP_SQL,
    down_sql=DOWN_SQL,
    created_at=datetime.now(timezone.utc)
)
