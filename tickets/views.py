from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Ticket
from .forms import TicketForm

# List all tickets
@login_required
def ticket_list(request):
    tickets = Ticket.objects.all().order_by('-created_at')
    return render(request, 'tickets/ticket_list.html', {'tickets': tickets})

# View a single ticket
@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})

# Create a new ticket
@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            messages.success(request, 'Your ticket has been created.')
            return redirect('tickets:ticket_list')  # <- namespace added
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form})

# Claim a ticket (for technicians)
@login_required
def ticket_claim(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if ticket.status == 'New':
        ticket.assigned_to = request.user
        ticket.status = 'Pending'
        ticket.save()
        messages.success(request, 'You have claimed this ticket.')
    else:
        messages.warning(request, 'This ticket has already been claimed.')
    return redirect('tickets:ticket_detail', pk=pk)  # <- namespace added

# Escalate a ticket
@login_required
def ticket_escalate(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        level = request.POST.get('level')
        if level in ['2', '3']:
            ticket.escalation_level = int(level)
            ticket.status = 'Pending'
            ticket.save()
            messages.success(request, f'Ticket escalated to Level {level} support.')
        return redirect('tickets:ticket_detail', pk=pk)  # <- namespace added
    return render(request, 'tickets/ticket_escalate.html', {'ticket': ticket})

# Close a ticket
@login_required
def ticket_close(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        resolution = request.POST.get('resolution')
        ticket.resolution = resolution
        ticket.status = 'Resolved'
        ticket.save()
        messages.success(request, 'Ticket closed successfully.')
        return redirect('tickets:ticket_list')  # <- namespace added
    return render(request, 'tickets/ticket_close.html', {'ticket': ticket})