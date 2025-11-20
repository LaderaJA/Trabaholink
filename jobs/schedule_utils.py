"""
Schedule management and conflict detection utilities for worker contracts.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from django.db.models import Q
from .models import Contract


def check_schedule_conflicts(
    worker_id: int,
    start_date: datetime.date,
    end_date: Optional[datetime.date] = None,
    exclude_contract_id: Optional[int] = None
) -> Tuple[bool, List[Contract], str]:
    """
    Check if a new contract conflicts with existing active contracts.
    
    Args:
        worker_id: ID of the worker
        start_date: Proposed start date
        end_date: Proposed end date (optional)
        exclude_contract_id: Contract ID to exclude from check (for updates)
    
    Returns:
        Tuple of (has_conflict, conflicting_contracts, warning_message)
    """
    # Get active contracts for the worker
    active_contracts = Contract.objects.filter(
        worker_id=worker_id,
        status__in=['Accepted', 'In Progress', 'Finalized', 'Awaiting Review']
    ).exclude(
        start_date__isnull=True
    )
    
    if exclude_contract_id:
        active_contracts = active_contracts.exclude(id=exclude_contract_id)
    
    conflicting_contracts = []
    
    for contract in active_contracts:
        # Check for overlap
        contract_start = contract.start_date
        contract_end = contract.end_date
        
        # If no end date specified, assume ongoing (30 days buffer)
        if not end_date:
            check_end = start_date + timedelta(days=30)
        else:
            check_end = end_date
        
        if not contract_end:
            # Ongoing contract - check if new contract starts before or during
            if start_date <= contract_start + timedelta(days=30):
                conflicting_contracts.append(contract)
        else:
            # Check for date range overlap
            if (start_date <= contract_end and check_end >= contract_start):
                conflicting_contracts.append(contract)
    
    has_conflict = len(conflicting_contracts) > 0
    
    if has_conflict:
        conflict_details = []
        for contract in conflicting_contracts:
            end_str = contract.end_date.strftime('%b %d, %Y') if contract.end_date else 'Ongoing'
            conflict_details.append(
                f"{contract.job.title} ({contract.start_date.strftime('%b %d, %Y')} - {end_str})"
            )
        
        warning_message = (
            f"⚠️ Schedule Conflict Detected!\n\n"
            f"This contract overlaps with {len(conflicting_contracts)} existing contract(s):\n"
            f"• " + "\n• ".join(conflict_details) + "\n\n"
            f"Please ensure you can manage multiple commitments or adjust the schedule."
        )
    else:
        warning_message = ""
    
    return has_conflict, conflicting_contracts, warning_message


def get_worker_schedule(worker_id: int, start_date: datetime.date, end_date: datetime.date) -> List[Dict]:
    """
    Get all scheduled contracts for a worker within a date range.
    
    Args:
        worker_id: ID of the worker
        start_date: Start of date range
        end_date: End of date range
    
    Returns:
        List of contract dictionaries with schedule info
    """
    contracts = Contract.objects.filter(
        worker_id=worker_id,
        status__in=['Accepted', 'In Progress', 'Finalized', 'Awaiting Review', 'Completed']
    ).exclude(
        start_date__isnull=True
    ).filter(
        Q(start_date__lte=end_date) &
        (Q(end_date__gte=start_date) | Q(end_date__isnull=True))
    ).select_related('job', 'client').order_by('start_date')
    
    # Vibrant, contrasting colors for different contracts
    vibrant_colors = [
        '#FF6B35',  # Vibrant Orange
        '#F7B801',  # Golden Yellow
        '#E63946',  # Red
        '#06FFA5',  # Mint Green
        '#4ECDC4',  # Turquoise
        '#9B59B6',  # Purple
        '#FF1744',  # Pink Red
        '#00BCD4',  # Cyan
        '#FF9800',  # Amber
        '#8BC34A',  # Light Green
        '#FF5722',  # Deep Orange
        '#FFEB3B',  # Yellow
        '#E91E63',  # Pink
        '#00E676',  # Green
        '#FFC107',  # Bright Amber
    ]
    
    schedule_items = []
    active_contract_idx = 0  # Counter for active contracts only
    
    for contract in contracts:
        # For completed contracts, use gray color and striped pattern
        if contract.status == 'Completed':
            color = '#9CA3AF'  # Gray for completed
            text_color = '#4B5563'  # Darker gray text
            display_style = 'background'  # Background style for completed
        else:
            # Assign a unique vibrant color to each active contract
            color = vibrant_colors[active_contract_idx % len(vibrant_colors)]
            text_color = '#FFFFFF'
            display_style = 'block'
            active_contract_idx += 1
        
        # If contract has end date, add 1 day (FullCalendar end date is exclusive)
        # This ensures all days including the end date are highlighted
        # If no end date, add 1 day to show at least one day on calendar
        if contract.end_date:
            end_date = (contract.end_date + timedelta(days=1)).isoformat()
        else:
            end_date = (contract.start_date + timedelta(days=1)).isoformat()
        
        # Add status indicator to title for completed contracts
        title = contract.job.title
        if contract.status == 'Completed':
            title = f"✓ {title} (Completed)"
        
        schedule_items.append({
            'id': contract.id,
            'title': title,
            'start': contract.start_date.isoformat(),
            'end': end_date,
            'allDay': True,  # This makes the event span full days
            'status': contract.status,
            'color': color,
            'textColor': text_color,
            'client': contract.client.get_full_name() or contract.client.username,
            'rate': str(contract.agreed_rate) if contract.agreed_rate else None,
            'url': f'/contract/{contract.id}/',
            'description': f"{contract.job.title} - {contract.client.get_full_name() or contract.client.username} ({contract.status})",
            'borderColor': color,
            'display': display_style,
            'classNames': ['completed-contract'] if contract.status == 'Completed' else [],
        })
    
    return schedule_items


def get_upcoming_deadlines(worker_id: int, days_ahead: int = 7) -> List[Dict]:
    """
    Get upcoming contract deadlines for a worker.
    
    Args:
        worker_id: ID of the worker
        days_ahead: Number of days to look ahead
    
    Returns:
        List of deadline dictionaries
    """
    today = datetime.now().date()
    future_date = today + timedelta(days=days_ahead)
    
    contracts = Contract.objects.filter(
        worker_id=worker_id,
        status__in=['In Progress', 'Awaiting Review'],
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=future_date
    ).select_related('job', 'client').order_by('end_date')
    
    deadlines = []
    for contract in contracts:
        days_remaining = (contract.end_date - today).days
        urgency = 'high' if days_remaining <= 2 else 'medium' if days_remaining <= 5 else 'low'
        
        deadlines.append({
            'contract_id': contract.id,
            'title': contract.job.title,
            'client': contract.client.get_full_name() or contract.client.username,
            'deadline': contract.end_date,
            'days_remaining': days_remaining,
            'urgency': urgency,
            'status': contract.status,
        })
    
    return deadlines


def calculate_workload(worker_id: int, date: datetime.date) -> Dict:
    """
    Calculate workload for a specific date.
    
    Args:
        worker_id: ID of the worker
        date: Date to check
    
    Returns:
        Dictionary with workload info
    """
    active_contracts = Contract.objects.filter(
        worker_id=worker_id,
        status__in=['In Progress', 'Awaiting Review'],
        start_date__lte=date
    ).filter(
        Q(end_date__gte=date) | Q(end_date__isnull=True)
    ).select_related('job', 'client')
    
    contract_count = active_contracts.count()
    
    # Determine workload level
    if contract_count == 0:
        level = 'none'
        message = 'No active contracts'
    elif contract_count == 1:
        level = 'light'
        message = '1 active contract'
    elif contract_count == 2:
        level = 'moderate'
        message = '2 active contracts'
    else:
        level = 'heavy'
        message = f'{contract_count} active contracts'
    
    return {
        'date': date,
        'contract_count': contract_count,
        'level': level,
        'message': message,
        'contracts': list(active_contracts.values('id', 'job__title', 'client__username'))
    }
