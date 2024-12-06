import React, { useState, useEffect } from 'react';
import { Form, Button, Alert } from 'react-bootstrap';
import apiClient from '../../../services/api';

function AlertConfig({ selectedDatabase, refreshAlerts }) {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [columns, setColumns] = useState([]);
  const [formData, setFormData] = useState({
    alert_title: '',
    alert_message: '',
    field_name: '',
    lower_bound: '',
    higher_bound: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Fetch tables when database is selected
  useEffect(() => {
    const fetchTables = async () => {
      try {
        console.log('Fetching tables for database:', selectedDatabase);
        const response = await apiClient.get(`/fault_management/tables_from_db?database=${selectedDatabase}`);
        console.log('Tables response:', response.data);
        setTables(response.data.tables);
        setSelectedTable(''); // Reset table selection when database changes
      } catch (error) {
        console.error('Error fetching tables:', error);
        setError('Failed to fetch tables');
      }
    };

    if (selectedDatabase) {
      fetchTables();
    }
  }, [selectedDatabase]);

  // Fetch columns when table is selected
  useEffect(() => {
    const fetchColumns = async () => {
      if (!selectedTable) return;
      
      try {
        console.log('Fetching columns for table:', selectedTable);
        const response = await apiClient.get(`/fault_management/columns_from_db?database=${selectedDatabase}&table=${selectedTable}`);
        console.log('Columns response:', response.data);
        setColumns(response.data.columns);
        setFormData(prev => ({ ...prev, field_name: '' })); // Reset field selection
      } catch (error) {
        console.error('Error fetching columns:', error);
        setError('Failed to fetch columns');
      }
    };

    if (selectedTable) {
      fetchColumns();
    }
  }, [selectedTable, selectedDatabase]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      await apiClient.post(`/fault_management/add_alert?database=${selectedDatabase}`, formData);
      setSuccess('Alert added successfully');
      refreshAlerts();
      // Reset form
      setFormData({
        alert_title: '',
        alert_message: '',
        field_name: '',
        lower_bound: '',
        higher_bound: ''
      });
    } catch (error) {
      setError('Failed to add alert');
      console.error('Error adding alert:', error);
    }
  };

  return (
    <div className="alert-config-container">
      <h3>Configure New Alert</h3>
      {error && <Alert variant="danger">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}
      
      <Form onSubmit={handleSubmit}>
        {/* Table Selection */}
        <Form.Group className="mb-3">
          <Form.Label>Select Table</Form.Label>
          <Form.Control
            as="select"
            value={selectedTable}
            onChange={(e) => setSelectedTable(e.target.value)}
            required
          >
            <option value="">Select a table</option>
            {tables.map((table) => (
              <option key={table} value={table}>
                {table}
              </option>
            ))}
          </Form.Control>
        </Form.Group>

        {/* Field Selection - only show if table is selected */}
        {selectedTable && (
          <Form.Group className="mb-3">
            <Form.Label>Select Field</Form.Label>
            <Form.Control
              as="select"
              value={formData.field_name}
              onChange={(e) => setFormData({ ...formData, field_name: e.target.value })}
              required
            >
              <option value="">Select a field</option>
              {columns.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </Form.Control>
          </Form.Group>
        )}

        {/* Other form fields */}
        <Form.Group className="mb-3">
          <Form.Label>Alert Title</Form.Label>
          <Form.Control
            type="text"
            value={formData.alert_title}
            onChange={(e) => setFormData({ ...formData, alert_title: e.target.value })}
            required
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Alert Message</Form.Label>
          <Form.Control
            type="text"
            value={formData.alert_message}
            onChange={(e) => setFormData({ ...formData, alert_message: e.target.value })}
            required
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Lower Bound</Form.Label>
          <Form.Control
            type="number"
            value={formData.lower_bound}
            onChange={(e) => setFormData({ ...formData, lower_bound: parseFloat(e.target.value) })}
            required
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Higher Bound</Form.Label>
          <Form.Control
            type="number"
            value={formData.higher_bound}
            onChange={(e) => setFormData({ ...formData, higher_bound: parseFloat(e.target.value) })}
            required
          />
        </Form.Group>

        <Button variant="primary" type="submit">
          Add Alert
        </Button>
      </Form>
    </div>
  );
}

export default AlertConfig;
