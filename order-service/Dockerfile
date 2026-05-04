FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 80

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY OrderService/OrderService.sln .

COPY OrderService/order-service.API/*.csproj order-service.API/
COPY OrderService/order-service.Application/*.csproj order-service.Application/
COPY OrderService/order-service.Domain/*.csproj order-service.Domain/
COPY OrderService/order-service.Infrastructure/*.csproj order-service.Infrastructure/

RUN dotnet restore

COPY OrderService/. .

WORKDIR /src/order-service.API
RUN dotnet publish -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=build /app/publish .

ENTRYPOINT ["dotnet", "order-service.API.dll"]