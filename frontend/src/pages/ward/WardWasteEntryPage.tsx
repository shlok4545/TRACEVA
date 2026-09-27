import { ClipboardPlus, Plus } from 'lucide-react';
import { useState } from 'react';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

export function WardWasteEntryPage() {
  const { token, user } = useAuth();
  const [itemName, setItemName] = useState('Used IV tubing');
  const [sourceDepartment, setSourceDepartment] = useState('Emergency');
  const [quantity, setQuantity] = useState('12');
  const [weightKg, setWeightKg] = useState('4.5');
  const [contaminationLevel, setContaminationLevel] = useState('HIGH');
  const [condition, setCondition] = useState('INTACT');
  const [description, setDescription] = useState('Clinical infectious waste generated during patient handling.');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<{ passportNumber?: string; status?: string; riskPriority?: string; warning?: string } | null>(null);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!token || !user) {
      setError('You must be signed in to create a passport.');
      return;
    }

    if (!itemName.trim() || !sourceDepartment.trim() || !quantity.trim()) {
      setError('Item name, source department, and quantity are required.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      setResult(null);

      const passport = await api.createPassport(token, {
        facility_id: user.facility_id ?? undefined,
        ward_id: user.ward_id ?? undefined,
        items: [{
          item_name: itemName,
          item_description: description,
          source_department: sourceDepartment,
          contamination_level: contaminationLevel,
          condition,
          quantity: Number(quantity),
          weight_kg: Number(weightKg || 0),
        }],
      });

      const classified = await api.classifyPassport(token, passport.id);
      setResult({
        passportNumber: passport.passport_number,
        status: classified.status,
        riskPriority: classified.risk_priority,
        warning: classified.classified_items[0]?.guidance ?? 'Classification generated successfully.',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/"/g, '') : 'Unable to create the waste passport.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 min-h-0 w-full">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Ward operations</p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-900">Waste Entry</h1>
        </div>
        <Button variant="primary" size="md" onClick={handleSubmit} disabled={isSubmitting}>
          <Plus className="mr-2" size={16} />
          {isSubmitting ? 'Creating...' : 'Create Waste Passport'}
        </Button>
      </div>

      <Card>
        <div className="mb-5 flex items-center gap-3">
          <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
            <ClipboardPlus size={20} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Document new waste batch</h2>
            <p className="text-sm text-slate-500">Create a real waste passport and run classification on the backend.</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Input label="Waste item" value={itemName} onChange={(event) => setItemName(event.target.value)} placeholder="Used IV tubing" />
          <Input label="Source department" value={sourceDepartment} onChange={(event) => setSourceDepartment(event.target.value)} placeholder="Emergency / ICU / Pathology" />
          <Input label="Quantity" type="number" min="0" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="12" />
          <Input label="Weight (kg)" type="number" min="0" step="0.1" value={weightKg} onChange={(event) => setWeightKg(event.target.value)} placeholder="4.5" />
          <Select label="Contamination level" value={contaminationLevel} onChange={(event) => setContaminationLevel(event.target.value)}>
            <option value="LOW">LOW</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="HIGH">HIGH</option>
            <option value="CRITICAL">CRITICAL</option>
          </Select>
          <Select label="Condition" value={condition} onChange={(event) => setCondition(event.target.value)}>
            <option value="INTACT">INTACT</option>
            <option value="DAMAGED">DAMAGED</option>
            <option value="LEAKING">LEAKING</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </Select>
          <div className="md:col-span-2">
            <Input label="Description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Clinical infectious waste generated during patient handling." />
          </div>
        </div>

        {error && <div className="mt-6 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
        {result && (
          <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            <div className="font-semibold">Passport created successfully</div>
            <div className="mt-1">ID: {result.passportNumber}</div>
            <div>Status: {result.status}</div>
            <div>Risk: {result.riskPriority}</div>
            <div className="mt-1">Guidance: {result.warning}</div>
          </div>
        )}
      </Card>
    </div>
  );
}
