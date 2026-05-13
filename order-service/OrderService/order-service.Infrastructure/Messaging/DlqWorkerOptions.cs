namespace order_service.Infrastructure.Messaging;

// Registre uma instância de DlqWorkerOptions por DLQ que deseja monitorar
public sealed record DlqWorkerOptions(
    // Nome da fila DLQ que este worker deve consumir
    string Queue
);
