"""
Celery tasks for KPI scoring engine.
"""
import logging
from datetime import date
from typing import Optional

from celery import shared_task
from django.db import transaction

from .models import KPI, KPIValue, KPIScore
from .utils import compute_kpi_score, aggregate_kpi_to_period, get_aggregation_strategy_for_kpi, get_period_bounds
from strategy.models import Objective

logger = logging.getLogger(__name__)


class Period:
    """Helper class to represent a time period."""
    
    def __init__(self, start_iso: str, end_iso: str):
        """
        Initialize Period from ISO date strings.
        
        Args:
            start_iso: ISO format date string (YYYY-MM-DD)
            end_iso: ISO format date string (YYYY-MM-DD)
        """
        self.start = date.fromisoformat(start_iso)
        self.end = date.fromisoformat(end_iso)
    
    @classmethod
    def from_dates(cls, start: date, end: date):
        """Create Period from date objects."""
        return cls(start.isoformat(), end.isoformat())


def compute_and_save_kpi_score(kpi: KPI, kpi_value: KPIValue) -> Optional[KPIScore]:
    """
    Compute and save KPI score for a given KPI and KPIValue.
    If a score already exists, it will be updated.
    
    Args:
        kpi: The KPI instance
        kpi_value: The KPIValue instance
        
    Returns:
        KPIScore instance or None if computation failed
    """
    try:
        # Check if score already exists (OneToOne relationship)
        try:
            existing_score = kpi_value.score
            # Delete existing score before creating new one
            existing_score.delete()
        except KPIScore.DoesNotExist:
            # No existing score, will create new one
            pass
        
        # Compute and create new score
        return compute_kpi_score(kpi, kpi_value)
        
    except Exception as e:
        logger.error(
            f"Error computing score for KPI {kpi.code} (value ID: {kpi_value.id}): {str(e)}",
            exc_info=True
        )
        return None


def compute_objective_score(objective: Objective, period: Period) -> Optional[float]:
    """
    Compute aggregated score for an objective based on its KPIs.
    
    This function:
    1. Finds all KPIs linked to the objective
    2. Normalizes their values to the objective's period
    3. Aggregates weighted scores
    
    Args:
        objective: The Objective instance
        period: The Period to compute scores for
        
    Returns:
        Aggregated objective score (float) or None if no KPIs/data available
    """
    try:
        # Get all KPIs linked to this objective
        kpis = KPI.objects.filter(objective=objective)
        
        if not kpis.exists():
            logger.debug(f"No KPIs found for objective {objective.id}")
            return None
        
        # Determine objective's reporting period (default to monthly)
        # This could be stored in objective metadata or inferred
        objective_period_type = "monthly"  # Default, could be from objective.metadata
        
        # Aggregate scores for each KPI
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for kpi in kpis:
            try:
                # Get aggregation strategy for this KPI
                aggregation_strategy = get_aggregation_strategy_for_kpi(kpi)
                
                # Aggregate KPI values to objective period
                aggregated_actual = aggregate_kpi_to_period(
                    kpi=kpi,
                    target_period_start=period.start,
                    target_period_end=period.end,
                    aggregation_strategy=aggregation_strategy
                )
                
                if aggregated_actual is None:
                    logger.debug(f"No data available for KPI {kpi.code} in period {period.start} to {period.end}")
                    continue
                
                # Get or create KPIValue for this period (for scoring)
                kpi_value, created = KPIValue.objects.get_or_create(
                    kpi=kpi,
                    period_start=period.start,
                    period_end=period.end,
                    defaults={'actual': aggregated_actual}
                )
                
                if not created and kpi_value.actual != aggregated_actual:
                    # Update with aggregated value
                    kpi_value.actual = aggregated_actual
                    kpi_value.save()
                
                # Compute score for this KPI value
                kpi_score = compute_and_save_kpi_score(kpi, kpi_value)
                
                if kpi_score:
                    # Add weighted score to total
                    weight = float(kpi.weight)
                    total_weighted_score += float(kpi_score.weighted_score) * weight
                    total_weight += weight
                    
            except Exception as e:
                logger.error(
                    f"Error processing KPI {kpi.code} for objective {objective.id}: {str(e)}",
                    exc_info=True
                )
                continue
        
        if total_weight == 0:
            logger.debug(f"No valid scores computed for objective {objective.id}")
            return None
        
        # Calculate final objective score
        objective_score = total_weighted_score / total_weight
        
        # Store objective score (this could be in a separate ObjectiveScore model)
        # For now, we'll log it or store in metadata
        logger.info(
            f"Objective {objective.id} ({objective.name}) score for period "
            f"{period.start} to {period.end}: {objective_score:.2f}"
        )
        
        return objective_score
        
    except Exception as e:
        logger.error(
            f"Error computing objective score for objective {objective.id}: {str(e)}",
            exc_info=True
        )
        return None


@shared_task(bind=True, max_retries=3)
def run_period_scoring(self, period_start_iso: str, period_end_iso: str):
    """
    Celery task to compute KPI scores and objective scores for a given period.
    
    Args:
        period_start_iso: ISO format date string for period start (YYYY-MM-DD)
        period_end_iso: ISO format date string for period end (YYYY-MM-DD)
    """
    try:
        period = Period(period_start_iso, period_end_iso)
        
        with transaction.atomic():
            # Process all KPI values for this period
            kpi_values = KPIValue.objects.filter(
                period_start=period.start,
                period_end=period.end
            ).select_related('kpi')
            
            processed_count = 0
            error_count = 0
            
            for kv in kpi_values:
                try:
                    compute_and_save_kpi_score(kv.kpi, kv)
                    processed_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Error computing score for KPIValue {kv.id} (KPI: {kv.kpi.code}): {str(e)}",
                        exc_info=True
                    )
                    # Continue processing other KPIs
                    continue
            
            logger.info(
                f"Processed {processed_count} KPI scores, {error_count} errors "
                f"for period {period.start} to {period.end}"
            )
            
            # After KPIs, run objective aggregation
            objectives = Objective.objects.all()
            objective_count = 0
            
            for obj in objectives:
                try:
                    score = compute_objective_score(obj, period)
                    if score is not None:
                        objective_count += 1
                except Exception as e:
                    logger.error(
                        f"Error computing objective score for objective {obj.id}: {str(e)}",
                        exc_info=True
                    )
                    continue
            
            logger.info(
                f"Computed scores for {objective_count} objectives "
                f"for period {period.start} to {period.end}"
            )
            
    except Exception as e:
        logger.error(
            f"Error in run_period_scoring task for period {period_start_iso} to {period_end_iso}: {str(e)}",
            exc_info=True
        )
        # Retry the task
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

