const { fakerFR: faker } = require('@faker-js/faker');
const { Client } = require('pg');

const NUMBER_ENTREE_DB = 500000

// Configuration de la connexion à la base de données
const client = new Client({
  user: 'feed_incident',
  host: 'localhost',
  database: 'feed_incident',
  password: 'feed_incident',
  port: 5432,
});

// Types d'incidents possibles
const incidentTypes = [
  { id: 1, name: 'naturel' },
  { id: 2, name: 'aggression' },
  { id: 3, name: 'vole' },
  { id: 4, name: 'incendie' },
  { id: 5, name: 'accident' },
  { id: 6, name: 'autre' },
  { id: 7, name: 'arme' },
];

// Génère une latitude/longitude aléatoire en France
//function getRandomFrenchCoordinates() {
  // Approximation des limites géographiques de la France métropolitaine
//  const lat = faker.location.latitude({ min: 41.3, max: 51.1 });
//  const long = faker.location.longitude({ min: -5.1, max: 9.6 });
//  return { lat, long };
//}
function getRandomFrenchCoordinates() {
  // Limites englobant tes 4 points
  const minLat = 48.62;
  const maxLat = 49.05;
  const minLong = 1.82;
  const maxLong = 2.70;

  const lat = faker.location.latitude({ min: minLat, max: maxLat });
  const long = faker.location.longitude({ min: minLong, max: maxLong });

  return { lat, long };
}


// Génère une date aléatoire dans du mois derniers
function getRandomDate() {
  const today = new Date();
  const end = new Date(today);
  const start = new Date(today);
  start.setMonth(today.getMonth() - 2);
  return faker.date.between({ from: start, to: end });
}

// Génère un script SQL pour insérer des incidents
function generateIncidents() {
  let incidents = [];
  for (let i = 0; i < NUMBER_ENTREE_DB; i++) {
    const declaredAt = getRandomDate();
    const isClosed = true;
    const closedAt = faker.date.between({
          from: new Date(declaredAt.getTime() + 60 * 60 * 1000),
          to: new Date(declaredAt.getTime() + 4 * 60 * 60 * 1000)});
    const { lat, long } = getRandomFrenchCoordinates();
    const typeId = faker.helpers.arrayElement(incidentTypes).id;

    incidents.push(`
      (
        ${i + 1},
        ${faker.number.int({ min: 1, max: 100 })},
        ${typeId},
        '${declaredAt.toISOString()}',
        ${closedAt ? `'${closedAt.toISOString()}'` : 'NULL'},
        '${faker.lorem.sentences({ min: 1, max: 3 })}',
        ${lat},
        ${long},
        ${isClosed},
        INTERVAL '60 minutes',
        ${faker.number.int({ min: 1, max: 10 })},
        ${faker.number.int({ min: 1, max: 10 })}
      )
    `);
  }
  return incidents.join(',');
}

//créé la table incident s si elle n'éxiste pas
async function createTableIfNotExists() {
  const query = `
    CREATE TABLE IF NOT EXISTS incidents (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL,
      type_id INTEGER NOT NULL,
      declared_at TIMESTAMP NOT NULL,
      closed_at TIMESTAMP NULL,
      description TEXT NOT NULL,
      location_latt DECIMAL(10, 8) NOT NULL,
      location_long DECIMAL(11, 8) NOT NULL,
      is_closed BOOLEAN NOT NULL DEFAULT FALSE,
      expire_incident INTERVAL NOT NULL DEFAULT '60 minutes',
      validation_count INTEGER NOT NULL CHECK (validation_count BETWEEN 1 AND 10),
      negation_count INTEGER NOT NULL CHECK (negation_count BETWEEN 1 AND 10)
    );
  `;
  await client.query(query);
}

async function main() {
  await client.connect();
  await createTableIfNotExists()
  const incidents = generateIncidents();

  const query = `
    INSERT INTO incidents(
      id, user_id, type_id, declared_at, closed_at, description,
      location_latt, location_long, is_closed, expire_incident, validation_count, negation_count
    ) VALUES ${incidents}
    ON CONFLICT (id) DO NOTHING;
  `;

  try {
    await client.query('BEGIN');
    await client.query(query);
    await client.query('COMMIT');
    console.log(NUMBER_ENTREE_DB +' : incidents insérés avec succès !');
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('Erreur lors de l\'insertion :', err);
  } finally {
    await client.end();
  }
}

main().catch(console.error);
