{{- define "cloudsweep.name" -}}
cloudsweep
{{- end }}

{{- define "cloudsweep.fullname" -}}
{{ include "cloudsweep.name" . }}
{{- end }}

{{- define "cloudsweep.labels" -}}
app.kubernetes.io/name: {{ include "cloudsweep.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "postgres.host" -}}
{{ include "cloudsweep.fullname" . }}-postgres
{{- end }}

{{- define "postgres.port" -}}
{{ .Values.postgres.port }}
{{- end }}

{{- define "postgres.database" -}}
{{ .Values.postgres.database }}
{{- end }}
