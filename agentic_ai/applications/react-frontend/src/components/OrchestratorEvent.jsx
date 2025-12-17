import React from 'react';
import { Card, CardContent, Box, Chip, Typography } from '@mui/material';
import { getOrchestratorDisplay } from '../utils/helpers.jsx';

/**
 * OrchestratorEvent component - Displays a single orchestrator event
 * @param {object} props
 * @param {object} props.event - Orchestrator event object
 */
export const OrchestratorEvent = ({ event }) => {
  const display = getOrchestratorDisplay(event.kind);

  return (
    <Card variant="outlined" sx={{ bgcolor: display.bgColor }}>
      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Chip
            icon={display.icon}
            label={display.label}
            size="small"
            color={display.color}
          />
        </Box>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {event.content}
        </Typography>
      </CardContent>
    </Card>
  );
};
