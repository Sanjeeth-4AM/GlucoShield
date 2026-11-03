"""Initial Phase 10 Normalized Schema

Revision ID: 0001_initial_phase10
Revises: 
Create Date: 2026-08-30 16:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_phase10'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Patient Profiles table
    op.create_table(
        'patient_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('patient_display_id', sa.String(length=64), nullable=False, server_default='patient_001'),
        sa.Column('age', sa.Float(), nullable=False, server_default='45.0'),
        sa.Column('bmi', sa.Float(), nullable=False, server_default='26.5'),
        sa.Column('diabetes_duration_years', sa.Float(), nullable=False, server_default='10.0'),
        sa.Column('hba1c', sa.Float(), nullable=False, server_default='58.0'),
        sa.Column('glycated_albumin', sa.Float(), nullable=False, server_default='18.0'),
        sa.Column('fasting_glucose', sa.Float(), nullable=False, server_default='130.0'),
        sa.Column('fasting_c_peptide', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('macrovascular_comp_count', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('microvascular_comp_count', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_t1dm', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patient_profiles_user_id'), 'patient_profiles', ['user_id'], unique=False)
    op.create_index(op.f('ix_patient_profiles_patient_display_id'), 'patient_profiles', ['patient_display_id'], unique=False)

    # 3. CGM Readings table
    op.create_table(
        'cgm_readings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('cgm_glucose', sa.Float(), nullable=False),
        sa.Column('insulin_bolus', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('insulin_basal', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('meal_carbs', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cgm_readings_patient_id'), 'cgm_readings', ['patient_id'], unique=False)
    op.create_index(op.f('ix_cgm_readings_timestamp'), 'cgm_readings', ['timestamp'], unique=False)
    op.create_index('idx_cgm_patient_time', 'cgm_readings', ['patient_id', 'timestamp'], unique=False)

    # 4. Insulin Records table
    op.create_table(
        'insulin_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('dose_type', sa.String(length=32), nullable=False, server_default='bolus'),
        sa.Column('units', sa.Float(), nullable=False),
        sa.Column('insulin_type', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_insulin_records_patient_id'), 'insulin_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_insulin_records_timestamp'), 'insulin_records', ['timestamp'], unique=False)

    # 5. Meal Records table
    op.create_table(
        'meal_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('meal_name', sa.String(length=255), nullable=False),
        sa.Column('portion_g', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('carbs_g', sa.Float(), nullable=False),
        sa.Column('calories_kcal', sa.Float(), nullable=True),
        sa.Column('protein_g', sa.Float(), nullable=True),
        sa.Column('fat_g', sa.Float(), nullable=True),
        sa.Column('user_confirmed', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meal_records_patient_id'), 'meal_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_meal_records_timestamp'), 'meal_records', ['timestamp'], unique=False)

    # 6. Food Analysis Records table
    op.create_table(
        'food_analysis_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('food_name_query', sa.String(length=255), nullable=True),
        sa.Column('selected_food', sa.String(length=255), nullable=True),
        sa.Column('portion_g', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('candidates', sa.JSON(), nullable=True),
        sa.Column('nutrition_density', sa.JSON(), nullable=True),
        sa.Column('final_macros', sa.JSON(), nullable=False),
        sa.Column('requires_user_confirmation', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('image_reference', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_food_analysis_records_patient_id'), 'food_analysis_records', ['patient_id'], unique=False)

    # 7. Forecast Records table
    op.create_table(
        'forecast_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('current_glucose', sa.Float(), nullable=False),
        sa.Column('current_iob', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('current_cob', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('point_forecast', sa.JSON(), nullable=False),
        sa.Column('lower_80', sa.JSON(), nullable=False),
        sa.Column('upper_80', sa.JSON(), nullable=False),
        sa.Column('lower_95', sa.JSON(), nullable=False),
        sa.Column('upper_95', sa.JSON(), nullable=False),
        sa.Column('hybrid_components', sa.JSON(), nullable=True),
        sa.Column('risk_assessment', sa.JSON(), nullable=False),
        sa.Column('explanation', sa.JSON(), nullable=False),
        sa.Column('disclaimer', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_forecast_records_patient_id'), 'forecast_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_forecast_records_timestamp'), 'forecast_records', ['timestamp'], unique=False)

    # 8. What-If Records table
    op.create_table(
        'what_if_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('scenario_name', sa.String(length=128), nullable=False, server_default='Custom Scenario'),
        sa.Column('scenario_meal_carbs_g', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('scenario_insulin_bolus_u', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('simulated_trajectory', sa.JSON(), nullable=False),
        sa.Column('nadir_glucose', sa.Float(), nullable=False),
        sa.Column('time_to_nadir_min', sa.Integer(), nullable=False),
        sa.Column('peak_glucose', sa.Float(), nullable=False),
        sa.Column('time_to_peak_min', sa.Integer(), nullable=False),
        sa.Column('time_in_range_pct', sa.Float(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_what_if_records_patient_id'), 'what_if_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_what_if_records_timestamp'), 'what_if_records', ['timestamp'], unique=False)

    # 9. Decision Records table
    op.create_table(
        'decision_records',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('food_analysis_id', sa.String(length=36), nullable=True),
        sa.Column('forecast_id', sa.String(length=36), nullable=True),
        sa.Column('what_if_id', sa.String(length=36), nullable=True),
        sa.Column('alert_status', sa.String(length=32), nullable=False, server_default='NORMAL'),
        sa.Column('recommended_action', sa.String(length=255), nullable=False),
        sa.Column('decision_summary', sa.JSON(), nullable=False),
        sa.Column('disclaimer', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['food_analysis_id'], ['food_analysis_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['forecast_id'], ['forecast_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['what_if_id'], ['what_if_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_decision_records_patient_id'), 'decision_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_decision_records_timestamp'), 'decision_records', ['timestamp'], unique=False)

    # 10. Wearable Observations table
    op.create_table(
        'wearable_observations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('patient_id', sa.String(length=36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('step_count', sa.Float(), nullable=True),
        sa.Column('heart_rate_bpm', sa.Float(), nullable=True),
        sa.Column('accel_magnitude_g', sa.Float(), nullable=True),
        sa.Column('device_source', sa.String(length=128), nullable=True, server_default='smartwatch'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wearable_observations_patient_id'), 'wearable_observations', ['patient_id'], unique=False)
    op.create_index(op.f('ix_wearable_observations_timestamp'), 'wearable_observations', ['timestamp'], unique=False)

def downgrade() -> None:
    op.drop_table('wearable_observations')
    op.drop_table('decision_records')
    op.drop_table('what_if_records')
    op.drop_table('forecast_records')
    op.drop_table('food_analysis_records')
    op.drop_table('meal_records')
    op.drop_table('insulin_records')
    op.drop_table('cgm_readings')
    op.drop_table('patient_profiles')
    op.drop_table('users')
