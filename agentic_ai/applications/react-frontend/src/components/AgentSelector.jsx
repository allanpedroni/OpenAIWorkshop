import React from 'react';
import {
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box,
  Typography,
} from '@mui/material';

/**
 * AgentSelector component - Dropdown for selecting active agent
 * @param {object} props
 * @param {Array} props.agents - Available agents
 * @param {string} props.currentAgent - Currently selected agent module path
 * @param {function} props.onChange - Change handler
 * @param {boolean} props.disabled - Whether selector is disabled
 */
export const AgentSelector = ({ agents, currentAgent, onChange, disabled }) => {
  return (
    <FormControl sx={{ minWidth: 250, mr: 2 }} size="small">
      <InputLabel id="agent-select-label" sx={{ color: 'white' }}>
        Active Agent
      </InputLabel>
      <Select
        labelId="agent-select-label"
        value={currentAgent}
        label="Active Agent"
        onChange={onChange}
        disabled={disabled}
        sx={{
          color: 'white',
          '.MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(255, 255, 255, 0.3)',
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(255, 255, 255, 0.5)',
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: 'white',
          },
          '.MuiSvgIcon-root': {
            color: 'white',
          },
        }}
      >
        {(Array.isArray(agents) ? agents : []).map((agent) => (
          <MenuItem key={agent.module_path} value={agent.module_path}>
            <Box>
              <Typography variant="body2">{agent.display_name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {agent.description}
              </Typography>
            </Box>
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
};
