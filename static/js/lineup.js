/**
 * Lineup Builder JavaScript
 * Handles drag-and-drop functionality for lineup management
 */

class LineupBuilder {
    constructor() {
        this.templateId = null;
        this.teamId = null;
        this.slots = [];
        this.availablePlayers = [];
        this.sortableInstances = [];
        this.warnings = [];
    }

    static init(config) {
        const builder = new LineupBuilder();
        builder.templateId = config.templateId;
        builder.teamId = config.teamId;
        builder.slots = config.slots || [];
        builder.availablePlayers = config.availablePlayers || [];
        
        builder.initializeSortable();
        builder.populateSlots();
        builder.setupEventListeners();
        
        window.LineupBuilder = builder;
        return builder;
    }

    initializeSortable() {
        // Initialize sortable for available players
        const availablePlayersEl = document.getElementById('availablePlayers');
        if (availablePlayersEl) {
            const availableSortable = new Sortable(availablePlayersEl, {
                group: 'lineup',
                animation: 150,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                onEnd: (evt) => this.handlePlayerMove(evt)
            });
            this.sortableInstances.push(availableSortable);
        }

        // Initialize sortable for each slot container
        const slotContainers = document.querySelectorAll('.slot-container');
        slotContainers.forEach(container => {
            const sortable = new Sortable(container, {
                group: 'lineup',
                animation: 150,
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                dragClass: 'sortable-drag',
                onEnd: (evt) => this.handlePlayerMove(evt)
            });
            this.sortableInstances.push(sortable);
        });
    }

    populateSlots() {
        // Populate slots with assigned players
        this.slots.forEach(slot => {
            if (slot.player_id && slot.player) {
                const slotContainer = document.querySelector(`[data-slot-id="${slot.id}"]`);
                if (slotContainer) {
                    this.addPlayerToSlot(slotContainer, slot.player);
                }
            }
        });
    }

    setupEventListeners() {
        // Setup save lineup button
        const saveBtn = document.querySelector('button[onclick="saveLineup()"]');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveLineup());
        }

        // Setup clear lineup button
        const clearBtn = document.querySelector('button[onclick="clearLineup()"]');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearLineup());
        }
    }

    handlePlayerMove(evt) {
        const { from, to, item } = evt;
        
        // Determine if moving to/from available players or slot
        const isToSlot = to.classList.contains('slot-container');
        const isFromSlot = from.classList.contains('slot-container');
        const isToAvailable = to.id === 'availablePlayers';
        const isFromAvailable = from.id === 'availablePlayers';

        if (isToSlot) {
            // Moving to a slot
            const slotId = to.dataset.slotId;
            const playerId = item.dataset.playerId;
            
            if (slotId && playerId) {
                this.assignPlayerToSlot(slotId, playerId);
            }
        } else if (isToAvailable) {
            // Moving to available players (removing from slot)
            const playerId = item.dataset.playerId;
            if (playerId) {
                this.removePlayerFromSlot(playerId);
            }
        }
    }

    async assignPlayerToSlot(slotId, playerId) {
        try {
            const response = await fetch(`/api/lineups/slots/${slotId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    slot_id: parseInt(slotId),
                    player_id: parseInt(playerId)
                })
            });

            const result = await response.json();
            
            if (result.success) {
                // Show warnings if any
                if (result.warnings && result.warnings.length > 0) {
                    this.showWarnings(result.warnings);
                } else {
                    this.hideWarnings();
                }
                
                CoachApp.showToast('Player assigned successfully', 'success');
            } else {
                throw new Error(result.message || 'Failed to assign player');
            }
        } catch (error) {
            CoachApp.showToast('Error assigning player: ' + error.message, 'error');
            // Revert the move
            this.revertMove();
        }
    }

    async removePlayerFromSlot(playerId) {
        // Find the slot this player was in
        const slotContainer = document.querySelector(`[data-slot-id] .player-card[data-player-id="${playerId}"]`);
        if (slotContainer) {
            const slotId = slotContainer.closest('.slot-container').dataset.slotId;
            
            try {
                const response = await fetch(`/api/lineups/slots/${slotId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        slot_id: parseInt(slotId),
                        player_id: null
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    CoachApp.showToast('Player removed successfully', 'success');
                } else {
                    throw new Error(result.message || 'Failed to remove player');
                }
            } catch (error) {
                CoachApp.showToast('Error removing player: ' + error.message, 'error');
                // Revert the move
                this.revertMove();
            }
        }
    }

    addPlayerToSlot(slotContainer, player) {
        // Clear existing content
        slotContainer.innerHTML = '';
        
        // Create player card
        const playerCard = document.createElement('div');
        playerCard.className = 'player-card slot-filled';
        playerCard.dataset.playerId = player.id;
        playerCard.dataset.playerName = player.name;
        playerCard.dataset.playerPosition = player.position;
        playerCard.dataset.playerJersey = player.jersey || '';
        playerCard.dataset.playerStatus = player.status;
        
        playerCard.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">
                        ${player.jersey ? `<span class="badge bg-primary me-2">${player.jersey}</span>` : ''}
                        ${player.name}
                    </h6>
                    <small class="text-muted">
                        <span class="badge position-${player.position.toLowerCase()} me-1">
                            ${player.position}
                        </span>
                        <span class="badge status-${player.status.toLowerCase()}">
                            ${player.status}
                        </span>
                    </small>
                </div>
                <i class="bi bi-grip-vertical text-muted"></i>
            </div>
        `;
        
        slotContainer.appendChild(playerCard);
    }

    showWarnings(warnings) {
        const banner = document.getElementById('warningsBanner');
        const list = document.getElementById('warningsList');
        
        if (banner && list) {
            list.innerHTML = '';
            warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning.message;
                list.appendChild(li);
            });
            
            banner.classList.remove('d-none');
        }
    }

    hideWarnings() {
        const banner = document.getElementById('warningsBanner');
        if (banner) {
            banner.classList.add('d-none');
        }
    }

    revertMove() {
        // This would need to be implemented to revert the visual move
        // For now, we'll just reload the page
        location.reload();
    }

    async saveLineup() {
        try {
            const response = await fetch(`/api/lineups/${this.templateId}/save`, {
                method: 'POST'
            });

            if (response.ok) {
                CoachApp.showToast('Lineup saved successfully!', 'success');
            } else {
                throw new Error('Failed to save lineup');
            }
        } catch (error) {
            CoachApp.showToast('Error saving lineup: ' + error.message, 'error');
        }
    }

    async clearLineup() {
        if (confirm('Are you sure you want to clear all player assignments? This action cannot be undone.')) {
            try {
                // Get all assigned slots
                const assignedSlots = [];
                const slotContainers = document.querySelectorAll('.slot-container');
                
                slotContainers.forEach(container => {
                    const slotId = container.dataset.slotId;
                    const playerCard = container.querySelector('.player-card[data-player-id]');
                    
                    if (slotId && playerCard) {
                        assignedSlots.push({
                            slot_id: parseInt(slotId),
                            player_id: null
                        });
                    }
                });

                if (assignedSlots.length > 0) {
                    const response = await fetch(`/api/lineups/${this.templateId}/slots`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            assignments: assignedSlots
                        })
                    });

                    const result = await response.json();
                    
                    if (result.success) {
                        CoachApp.showToast('Lineup cleared successfully!', 'success');
                        location.reload();
                    } else {
                        throw new Error('Failed to clear lineup');
                    }
                } else {
                    CoachApp.showToast('No players assigned to clear', 'info');
                }
            } catch (error) {
                CoachApp.showToast('Error clearing lineup: ' + error.message, 'error');
            }
        }
    }
}

// Global functions for backward compatibility
function saveLineup() {
    if (window.LineupBuilder) {
        window.LineupBuilder.saveLineup();
    }
}

function clearLineup() {
    if (window.LineupBuilder) {
        window.LineupBuilder.clearLineup();
    }
}
