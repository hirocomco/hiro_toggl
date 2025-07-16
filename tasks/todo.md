# Client-Specific Rates UI Improvement

## Problem
The current Admin page shows all clients in a grid format for rate management, but the user wants a simpler + button approach to add client-specific rates on demand.

## Current State
- Admin.tsx shows all clients in "Client-Specific Rates" section (lines 348-401)
- + button exists but hardcoded to first client (line 330)
- Interface is cluttered with all clients showing at once

## Tasks

### 🔄 High Priority  
- [ ] Remove the "Client-Specific Rates" section that shows all clients in a grid
- [ ] Implement proper + button functionality with client selection dropdown
- [ ] Add client-specific rate management directly in the member rows
- [ ] Test the simplified interface works correctly

### 📋 Medium Priority
- [ ] Update the rate form to include client selection when adding new rates
- [ ] Improve the display of existing client overrides in the table
- [ ] Add ability to remove client-specific rates

## Implementation Plan

1. **Remove Client Grid Section**: Delete the entire "Client-Specific Rates" card section
2. **Enhance + Button**: Replace hardcoded client selection with dropdown modal
3. **Inline Client Management**: Show client overrides more compactly in the member table
4. **Rate Form Enhancement**: Add client selection to the rate editing form

## Goals
- Simpler, cleaner interface
- On-demand client rate creation instead of showing all clients
- Better user experience with focused workflow