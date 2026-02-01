/**
 * ValidationPanel component for displaying validation errors and warnings.
 * Used in conjunction with StateEditor to show validation feedback.
 */
import React from 'react';

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

interface ValidationPanelProps {
  errors: ValidationError[];
  warnings?: ValidationError[];
  className?: string;
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  errors,
  warnings = [],
  className = '',
}) => {
  const allIssues = [
    ...errors.map((e) => ({ ...e, severity: 'error' as const })),
    ...warnings.map((w) => ({ ...w, severity: 'warning' as const })),
  ];

  if (allIssues.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {allIssues.map((issue, idx) => {
        const isError = issue.severity === 'error';
        const isWarning = issue.severity === 'warning';
        const isInfo = issue.severity === 'info';

        return (
          <div
            key={`${issue.severity}-${issue.field}-${idx}`}
            className={`flex items-start p-3 rounded-md border ${
              isError
                ? 'bg-red-50 border-red-200'
                : isWarning
                ? 'bg-yellow-50 border-yellow-200'
                : 'bg-blue-50 border-blue-200'
            }`}
          >
            <span
              className={`font-bold mr-2 ${
                isError
                  ? 'text-red-600'
                  : isWarning
                  ? 'text-yellow-600'
                  : 'text-blue-600'
              }`}
            >
              {isError ? '✕' : isWarning ? '⚠' : 'ℹ'}
            </span>
            <div className="flex-1">
              <div className="flex items-baseline gap-2">
                <span
                  className={`font-medium text-sm ${
                    isError
                      ? 'text-red-800'
                      : isWarning
                      ? 'text-yellow-800'
                      : 'text-blue-800'
                  }`}
                >
                  {issue.field}
                </span>
                <span
                  className={`text-xs uppercase font-semibold ${
                    isError
                      ? 'text-red-600'
                      : isWarning
                      ? 'text-yellow-600'
                      : 'text-blue-600'
                  }`}
                >
                  {issue.severity}
                </span>
              </div>
              <p
                className={`text-sm mt-1 ${
                  isError
                    ? 'text-red-700'
                    : isWarning
                    ? 'text-yellow-700'
                    : 'text-blue-700'
                }`}
              >
                {issue.message}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * ValidationSummary component for showing a compact summary of validation results.
 */
interface ValidationSummaryProps {
  errorCount: number;
  warningCount: number;
  className?: string;
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({
  errorCount,
  warningCount,
  className = '',
}) => {
  if (errorCount === 0 && warningCount === 0) {
    return (
      <div className={`flex items-center text-green-600 ${className}`}>
        <span className="mr-2">✓</span>
        <span className="text-sm font-medium">All validations passed</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-4 ${className}`}>
      {errorCount > 0 && (
        <div className="flex items-center text-red-600">
          <span className="mr-1">✕</span>
          <span className="text-sm font-medium">
            {errorCount} {errorCount === 1 ? 'error' : 'errors'}
          </span>
        </div>
      )}
      {warningCount > 0 && (
        <div className="flex items-center text-yellow-600">
          <span className="mr-1">⚠</span>
          <span className="text-sm font-medium">
            {warningCount} {warningCount === 1 ? 'warning' : 'warnings'}
          </span>
        </div>
      )}
    </div>
  );
};
