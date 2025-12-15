import React from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
  Card,
  CardContent,
  Box,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';
import { getAgentEmoji } from '../utils/helpers.jsx';

/**
 * AgentEvent component - Displays agent events with tool calls
 * @param {object} props
 * @param {string} props.agentId - Agent identifier
 * @param {object} props.agentData - Agent event data
 * @param {boolean} props.isActive - Whether agent is currently active
 */
export const AgentEvent = ({ agentId, agentData, isActive }) => {
  const agentEmoji = getAgentEmoji(agentId);

  return (
    <Accordion defaultExpanded={!agentData.complete}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <span style={{ fontSize: '1.2em' }}>{agentEmoji}</span>
          {agentData.name}
          {isActive && (
            <Chip label="Working..." size="small" color="secondary" />
          )}
          {agentData.complete && (
            <CheckIcon fontSize="small" color="success" />
          )}
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        {/* Tool calls grouped by turn */}
        {agentData.toolCallsByTurn && Object.keys(agentData.toolCallsByTurn).length > 0 && (
          <Box sx={{ mb: 1 }}>
            {Object.entries(agentData.toolCallsByTurn)
              .sort(([turnA], [turnB]) => Number(turnA) - Number(turnB))
              .map(([turn, tools]) => (
                <Box key={turn} sx={{ mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                    Turn {turn}:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', ml: 1 }}>
                    {tools.map((tool, idx) => (
                      <Chip
                        key={idx}
                        label={`🔧 ${tool}`}
                        size="small"
                        variant="outlined"
                        color="info"
                      />
                    ))}
                  </Box>
                </Box>
              ))}
          </Box>
        )}
        {/* Agent message */}
        <Card variant="outlined" sx={{ bgcolor: '#fff3e0' }}>
          <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
              {agentData.finalMessage || agentData.tokens.join('')}
            </Typography>
          </CardContent>
        </Card>
      </AccordionDetails>
    </Accordion>
  );
};
