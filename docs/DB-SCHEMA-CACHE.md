# HWB Institutional Database Schema Cache

This file serves as a local pre-cached reference of the PostgreSQL schema to eliminate expensive database exploratory queries and minimize token consumption.

### Table: ActivityLog
| Column | Data Type |
| :--- | :--- |
| id | integer |
| date | date |
| activity_name | text |
| hours | double precision |
| category | text |

### Table: Analytics
| Column | Data Type |
| :--- | :--- |
| tool_name | text |
| result | text |

### Table: COPQ
| Column | Data Type |
| :--- | :--- |
| id | integer |
| defect_type | text |
| impact | text |
| status | text |

### Table: Chemicals
| Column | Data Type |
| :--- | :--- |
| id | integer |
| name | text |
| product_id | text |
| hazard_level | text |
| intended_use | text |
| sds_link | text |
| timestamp | date |
| process_id | text |

### Table: ClientActivities
| Column | Data Type |
| :--- | :--- |
| id | integer |
| client_id | integer |
| activity_type | text |
| description | text |
| timestamp | date |

### Table: Contacts
| Column | Data Type |
| :--- | :--- |
| contact_id | integer |
| account_id | integer |
| full_name | text |
| role | text |
| email | text |
| phone | text |
| title | text |
| department | text |
| reports_to | integer |
| lead_id | integer |

### Table: CrewSync
| Column | Data Type |
| :--- | :--- |
| crew_member_id | integer |
| full_name | text |
| email | text |
| phone | text |
| role | text |
| current_status | text |
| last_gps_lat | double precision |
| last_gps_long | double precision |
| last_sync_at | date |
| auth_token | text |

### Table: Customers
| Column | Data Type |
| :--- | :--- |
| customer_id | integer |
| company_name | text |
| contact_person_name | text |
| company_address | text |
| city | text |
| zip | text |
| state | text |
| phone | text |
| email | text |
| quote_number | text |
| contract_period | text |
| frequency | text |
| start_date | date |
| start_time | text |
| payment_terms | text |
| website | text |
| billing_address | text |
| annual_revenue | double precision |
| assigned_rep_id | integer |
| notes | text |
| created_at | date |
| status | text |
| sqf | integer |
| traffic_cycle | text |

### Table: GlobalActivities
| Column | Data Type |
| :--- | :--- |
| activity_id | integer |
| parent_id | integer |
| parent_type | text |
| activity_type | text |
| description | text |
| timestamp | timestamp without time zone |

### Table: Incidents
| Column | Data Type |
| :--- | :--- |
| id | integer |
| date | date |
| description | text |
| category | text |
| severity | text |

### Table: KPIVs
| Column | Data Type |
| :--- | :--- |
| id | integer |
| metric_name | text |
| value | text |
| target | text |

### Table: Leads
| Column | Data Type |
| :--- | :--- |
| id | integer |
| job_title | text |
| center_name | text |
| email | text |
| wage | double precision |
| cleaning_hours | double precision |
| calculated_waste | double precision |
| timestamp | date |
| process_id | text |
| phone | text |
| address | text |
| county | text |
| zipcode | text |
| director | text |
| capacity | integer |
| city | text |
| state | text |
| industry | text |
| sqf | integer |
| input_date | date |
| status | text |
| is_converted | boolean |
| owner_id | integer |
| preferred_date | text |
| preferred_time | text |
| lead_source | text |
| service_interest | text |
| priority_level | text |
| facility_type | text |
| budget_range | text |
| next_action_date | text |
| estimated_annual_value | double precision |
| last_contacted_by | text |
| traffic_cycle | text |
| decision_maker | text |
| notes | text |
| updated_at | date |

### Table: Milestones
| Column | Data Type |
| :--- | :--- |
| id | integer |
| category | text |
| name | text |
| status | text |
| description | text |

### Table: Opportunities
| Column | Data Type |
| :--- | :--- |
| opp_id | integer |
| account_id | integer |
| stage | text |
| amount | double precision |
| expected_close | date |
| probability | integer |
| last_modified | date |

### Table: PendingOutbox
| Column | Data Type |
| :--- | :--- |
| id | integer |
| recipient | text |
| subject | text |
| body | text |
| created_at | date |
| status | text |

### Table: Readiness
| Column | Data Type |
| :--- | :--- |
| id | integer |
| category | text |
| item | text |
| status | text |

### Table: ScopeLibrary
| Column | Data Type |
| :--- | :--- |
| id | integer |
| category | text |
| value | text |

### Table: ServiceTasks
| Column | Data Type |
| :--- | :--- |
| task_id | integer |
| service_id | integer |
| area_name | text |
| task_category | text |
| task_description | text |
| created_at | date |

### Table: Services
| Column | Data Type |
| :--- | :--- |
| service_id | integer |
| customer_id | integer |
| service_requested | text |
| total_square_footage | integer |
| unit_price_per_sqf | double precision |
| unit_per_visit | double precision |
| extended_monthly_price | double precision |
| extended_yearly_estimate | double precision |
| quote_number | text |
| tasks_json | text |
| traffic_cycle | text |
| frequency | text |
| notes | text |
| status | text |

### Table: SigmaAbilities
| Column | Data Type |
| :--- | :--- |
| id | integer |
| ability_name | text |
| description | text |
| status | text |
| technical_requirements | text |
| created_at | timestamp without time zone |
| updated_at | timestamp without time zone |

### Table: SigmaInteractionCore
| Column | Data Type |
| :--- | :--- |
| id | integer |
| session_id | text |
| agent_id | text |
| user_prompt | text |
| agent_explanation | text |
| tools_used | jsonb |
| technical_data | jsonb |
| error_log | text |
| status | text |
| timestamp | timestamp without time zone |

### Table: SigmaInteractionLog
| Column | Data Type |
| :--- | :--- |
| id | integer |
| timestamp | timestamp without time zone |
| user_prompt | text |
| agent_explanation | text |
| tools_used | jsonb |
| status | character varying |

### Table: SigmaKnowledgeScars
| Column | Data Type |
| :--- | :--- |
| id | integer |
| description | text |
| category | text |
| status | text |
| impact_level | integer |
| root_cause | text |
| implemented_fix | text |
| preventative_rule | text |
| created_at | timestamp without time zone |
| resolved_at | timestamp without time zone |
| resolution_notes | text |

### Table: SigmaPrompts
| Column | Data Type |
| :--- | :--- |
| id | integer |
| agent_id | text |
| prompt_text | text |
| version | text |
| is_active | boolean |
| created_at | timestamp without time zone |
| updated_at | timestamp without time zone |

### Table: SigmaSystemCore
| Column | Data Type |
| :--- | :--- |
| id | integer |
| session_id | text |
| state_data | jsonb |
| markdown_parity_path | text |
| updated_at | timestamp without time zone |

### Table: SigmaTelemetry
| Column | Data Type |
| :--- | :--- |
| id | integer |
| session_id | character varying |
| timestamp | timestamp without time zone |
| objective | text |
| last_action | text |
| next_step | text |
| heat_zone_files | jsonb |
| technical_logic | jsonb |
| operator | character varying |
| status | character varying |

### Table: SigmaVault
| Column | Data Type |
| :--- | :--- |
| id | integer |
| key_name | text |
| secret_value | text |
| expiration_date | date |
| status | text |
| last_rotated | timestamp without time zone |
| notes | text |

### Table: SigmaWalkthroughs
| Column | Data Type |
| :--- | :--- |
| id | integer |
| session_id | text |
| project_name | text |
| narrative_content | text |
| impact_summary | jsonb |
| validation_results | text |
| created_at | timestamp without time zone |

### Table: SocialOutbox
| Column | Data Type |
| :--- | :--- |
| id | integer |
| platform | text |
| content | text |
| media_url | text |
| created_at | date |
| status | text |

### Table: SystemReleases
| Column | Data Type |
| :--- | :--- |
| id | integer |
| version | text |
| author | text |
| description | text |
| timestamp | timestamp without time zone |

### Table: SystemSettings
| Column | Data Type |
| :--- | :--- |
| key | text |
| value | text |

### Table: Uptime
| Column | Data Type |
| :--- | :--- |
| id | integer |
| timestamp | date |
| status | integer |

### Table: Users
| Column | Data Type |
| :--- | :--- |
| id | integer |
| username | text |
| password_hash | text |
| full_name | text |
| email | text |
| role | text |

### Table: Warchest
| Column | Data Type |
| :--- | :--- |
| id | integer |
| name | text |
| url | text |
| category | text |
| description | text |
| added_at | date |

### Table: WorkOrderSnapshots
| Column | Data Type |
| :--- | :--- |
| snapshot_id | integer |
| work_order_id | integer |
| snapshot_data | text |
| captured_at | date |

### Table: WorkOrders
| Column | Data Type |
| :--- | :--- |
| work_order_id | integer |
| customer_id | integer |
| service_id | integer |
| status | text |
| scheduled_date | date |
| scheduled_time | text |
| actual_start_time | text |
| actual_end_time | text |
| crew_lead_id | integer |
| client_notes | text |
| crew_notes | text |
| photo_proof_url | text |
| last_gps_lat | double precision |
| last_gps_long | double precision |
| created_at | date |

### Table: agent_task_state
| Column | Data Type |
| :--- | :--- |
| task_id | text |
| agent_id | text |
| current_step | integer |
| total_steps | integer |
| status | text |
| last_updated | timestamp without time zone |

### Table: alembic_version
| Column | Data Type |
| :--- | :--- |
| version_num | character varying |

### Table: clients
| Column | Data Type |
| :--- | :--- |
| id | integer |
| client_name | text |
| service_location | text |
| square_footage | integer |
| contact_name | text |
| contact_email | text |
| contact_phone | text |

### Table: routine_schedule
| Column | Data Type |
| :--- | :--- |
| routine_id | text |
| task_type | text |
| frequency_seconds | integer |
| last_run | timestamp without time zone |
| status | text |

### Table: sigma_kb
| Column | Data Type |
| :--- | :--- |
| id | integer |
| doc_id | text |
| content | text |
| search_vector | tsvector |
| embedding | ARRAY |
| metadata | jsonb |
| timestamp | timestamp without time zone |

### Table: task_queue
| Column | Data Type |
| :--- | :--- |
| task_id | text |
| task_type | text |
| priority | integer |
| payload | text |
| status | text |
| created_at | timestamp without time zone |
| started_at | timestamp without time zone |
| completed_at | timestamp without time zone |
