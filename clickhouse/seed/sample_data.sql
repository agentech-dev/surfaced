-- Sample data for quick start
-- Run with: clickhousectl local client --queries-file clickhouse/seed/sample_data.sql

-- Sample brand
INSERT INTO brands (id, name, domain, description, aliases, competitors)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Acme Corp',
    'acme.com',
    'A sample company for testing AI visibility tracking',
    ['Acme', 'ACME', 'Acme Corporation'],
    ['Globex', 'Initech', 'Umbrella Corp']
);

-- Sample provider
INSERT INTO providers (id, name, provider, execution_mode, model, rate_limit_rpm)
VALUES (
    '00000000-0000-0000-0000-000000000010',
    'Claude Sonnet',
    'anthropic',
    'api',
    'claude-sonnet-4-6',
    60
);

-- Sample prompts
INSERT INTO prompts (id, text, category, branded, tags, brand_id) VALUES
    ('00000000-0000-0000-0000-000000000100', 'What are the best project management tools?', 'project_management', false, ['daily'], '00000000-0000-0000-0000-000000000001'),
    ('00000000-0000-0000-0000-000000000101', 'Compare Acme Corp with its competitors in the market', 'project_management', true, ['weekly'], '00000000-0000-0000-0000-000000000001'),
    ('00000000-0000-0000-0000-000000000102', 'What software solutions are available for enterprise workflow automation?', 'workflow_automation', false, ['daily'], '00000000-0000-0000-0000-000000000001'),
    ('00000000-0000-0000-0000-000000000103', 'What are the key features to look for in a project management platform?', 'project_management', false, ['weekly'], '00000000-0000-0000-0000-000000000001'),
    ('00000000-0000-0000-0000-000000000104', 'How can I improve team collaboration and productivity?', 'team_productivity', false, ['monthly'], '00000000-0000-0000-0000-000000000001');
