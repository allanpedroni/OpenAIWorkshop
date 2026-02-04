import { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  Divider,
} from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';
import SendIcon from '@mui/icons-material/Send';
import { ACTION_OPTIONS } from '../constants/workflow';

/**
 * Panel for analyst to make decisions on fraud alerts (Durable version)
 * @param {Object} props - Component props
 * @param {Object} props.decision - Decision request object with instance_id, alert_id, customer_id
 * @param {Function} props.onSubmit - Callback to submit decision
 */
function AnalystDecisionPanel({ decision, onSubmit }) {
  const [selectedAction, setSelectedAction] = useState(
    decision.recommended_action || 'block'
  );
  const [notes, setNotes] = useState('');

  const handleSubmit = () => {
    onSubmit({
      instance_id: decision.instance_id,
      alert_id: decision.alert_id,
      customer_id: decision.customer_id,
      approved_action: selectedAction,
      analyst_notes: notes || 'Analyst decision from UI',
      analyst_id: 'analyst_ui',
    });
  };

  return (
    <Paper
      elevation={3}
      sx={{
        p: 1,
        display: 'flex',
        flexDirection: 'column',
        gap: 0.5,
        border: 2,
        borderColor: 'warning.main',
        animation: 'pulse 2s ease-in-out infinite',
        maxHeight: '50vh',
        overflow: 'auto',
        '@keyframes pulse': {
          '0%, 100%': { borderColor: '#ff9800' },
          '50%': { borderColor: '#ffc107' },
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <GavelIcon color="warning" fontSize="small" />
        <Typography variant="subtitle1" fontWeight="bold">Analyst Review Required</Typography>
      </Box>

      <Alert severity="warning" sx={{ py: 0.25, px: 1 }}>
        <Typography variant="caption" fontWeight="bold">
          Human Decision Needed
        </Typography>
      </Alert>

      <Divider sx={{ my: 0.5 }} />

      {/* Risk Assessment */}
      <Box>
        <Typography variant="caption" fontWeight="bold" display="block" sx={{ mb: 0.5 }}>
          Review Required
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center', mb: 0.5 }}>
          <Typography variant="caption">Alert ID:</Typography>
          <Chip label={decision.alert_id || 'N/A'} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
        </Box>
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
          <Typography variant="caption">Customer:</Typography>
          <Chip label={decision.customer_id || 'N/A'} size="small" variant="outlined" sx={{ height: 20, fontSize: '0.7rem' }} />
        </Box>
      </Box>

      {/* Instance Info */}
      <Box>
        <Typography variant="caption" fontWeight="bold" display="block" sx={{ mb: 0.5 }}>
          Instance ID
        </Typography>
        <Typography variant="caption" sx={{ wordBreak: 'break-all', fontSize: '0.65rem', opacity: 0.7 }}>
          {decision.instance_id}
        </Typography>
      </Box>

      <Divider sx={{ my: 0.5 }} />

      {/* Decision Form */}
      <FormControl fullWidth size="small" sx={{ minHeight: 40 }}>
        <InputLabel sx={{ fontSize: '0.875rem' }}>Your Decision</InputLabel>
        <Select
          value={selectedAction}
          label="Your Decision"
          onChange={(e) => setSelectedAction(e.target.value)}
          sx={{ fontSize: '0.875rem' }}
        >
          {ACTION_OPTIONS.map((option) => (
            <MenuItem key={option.value} value={option.value} sx={{ fontSize: '0.875rem' }}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      <TextField
        label="Analyst Notes"
        multiline
        rows={2}
        fullWidth
        size="small"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Add notes..."
        sx={{ '& .MuiInputBase-input': { fontSize: '0.875rem' } }}
      />

      <Button
        variant="contained"
        color="primary"
        size="small"
        fullWidth
        startIcon={<SendIcon fontSize="small" />}
        onClick={handleSubmit}
        sx={{ mt: 0.5, py: 0.75 }}
      >
        Submit Decision
      </Button>
    </Paper>
  );
}

export default AnalystDecisionPanel;
