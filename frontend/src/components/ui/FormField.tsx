interface FormFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  type?: string;
}

export function FormField({ label, value, onChange, placeholder, error, type = 'text' }: FormFieldProps) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <label style={{
        display: 'block',
        fontFamily: "var(--font-mono)",
<<<<<<< HEAD
        fontSize: '12px',
=======
        fontSize: '15px',
>>>>>>> feature/classroom-mode
        color: 'var(--text-dim)',
        textTransform: 'uppercase',
        letterSpacing: '1px',
        marginBottom: '6px',
      }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: '100%',
          padding: '12px 14px',
          background: 'var(--bg-primary)',
          border: `1px solid ${error ? 'var(--neon-red)' : 'var(--border-color)'}`,
          borderRadius: '4px',
          color: 'var(--text-primary)',
          fontFamily: "var(--font-mono)",
<<<<<<< HEAD
          fontSize: '14px',
=======
          fontSize: '17px',
>>>>>>> feature/classroom-mode
          outline: 'none',
          transition: 'border-color 0.2s ease',
        }}
        onFocus={(e) => {
          if (!error) e.currentTarget.style.borderColor = 'var(--neon-cyan)';
        }}
        onBlur={(e) => {
          if (!error) e.currentTarget.style.borderColor = 'var(--border-color)';
        }}
      />
      {error && (
        <div style={{
          fontFamily: "var(--font-mono)",
<<<<<<< HEAD
          fontSize: '12px',
=======
          fontSize: '15px',
>>>>>>> feature/classroom-mode
          color: 'var(--neon-red)',
          marginTop: '4px',
        }}>
          {error}
        </div>
      )}
    </div>
  );
}
